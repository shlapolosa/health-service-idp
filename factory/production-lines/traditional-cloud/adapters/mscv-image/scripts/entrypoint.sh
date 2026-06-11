#!/usr/bin/env bash
# HARD-1 (#168): microservice-creator (mscv) entrypoint.
#
# This is the BYTE-EQUIVALENT extraction of the ~288-line bash heredoc that
# previously lived inline in the `<service>-mscv` Job of
# factory/production-lines/traditional-cloud/adapters/composition/application-claim-composition.yaml.
#
# Behaviour preserved EXACTLY:
#   - same template selection (python/fastapi, rasa/chatbot, nodejs/graphql-gateway, java/springboot)
#   - same realtime flavor (agent_common vendoring + pyproject dep injection)  [RT-1 #156/#167]
#   - same EVENT-1 (#150) ordering assumption (no poll; single rebase before commit)
#   - same idempotent commit + UNIFY-1 (#153) rebase-push retry loop (max 10)
#   - same README / commit message text
#
# The lib/*.sh files are SOURCED (not exec'd) so that `cd` and shell variables
# persist across them exactly as in the original single-shell heredoc. The
# decomposition is structural only; no command order or text was changed.
#
# Contract (env vars, identical to the Job today):
#   SERVICE_NAME   - microservice name (also the ApplicationClaim spec.name)
#   APP_CONTAINER  - target monorepo (AppContainer) name
#   LANGUAGE       - python | rasa | nodejs | java
#   FRAMEWORK      - fastapi | chatbot | graphql-gateway | springboot
#   SERVICE_FLAVOR - webservice (default) | realtime
#   GITHUB_TOKEN   - PAT for clone/push (from github-credentials secret)
#   GITHUB_USER    - GitHub org/user (from github-credentials secret)
#   DOCKER_REGISTRY, DOCKER_USER - present in the Job env (unused by this script,
#                    kept for contract parity)
set -euo pipefail

# Resolve the directory this script lives in so the libs are found regardless
# of the working directory (the original ran everything from one inline shell).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

# shellcheck source=lib/template-select.sh
. "$LIB_DIR/template-select.sh"
# shellcheck source=lib/python-fastapi.sh
. "$LIB_DIR/python-fastapi.sh"
# shellcheck source=lib/rasa.sh
. "$LIB_DIR/rasa.sh"
# shellcheck source=lib/nodejs-graphql.sh
. "$LIB_DIR/nodejs-graphql.sh"
# shellcheck source=lib/java-springboot.sh
. "$LIB_DIR/java-springboot.sh"
# shellcheck source=lib/git-push-retry.sh
. "$LIB_DIR/git-push-retry.sh"

echo "Adding microservice $SERVICE_NAME to AppContainer $APP_CONTAINER..."

TEMP_DIR="/tmp/app-container-$APP_CONTAINER"
mkdir -p $TEMP_DIR
cd $TEMP_DIR

# Clone the AppContainer repository using GitHub token
git clone https://$GITHUB_TOKEN@github.com/$GITHUB_USER/$APP_CONTAINER.git .

# RECREATE-STORM (#175): NO-CLOBBER. A Crossplane reconcile / claim recreation can
# re-run this Job long after the service was scaffolded AND HAND-EDITED (or
# dev-agent-edited). Re-scaffolding overwrites src/main.py + vendored deps with a
# fresh template (exactly how rtdemo commit 8885dca regressed the gateway image).
# If the service dir already has an entrypoint artifact, scaffolding already
# happened — exit 0 (idempotent success; the composition only needs the Job green).
if [ -f "microservices/$SERVICE_NAME/src/main.py" ] \
   || [ -f "microservices/$SERVICE_NAME/package.json" ] \
   || [ -f "microservices/$SERVICE_NAME/pom.xml" ]; then
  echo "microservices/$SERVICE_NAME already scaffolded (entrypoint artifact present) - skipping re-scaffold (no-clobber)"
  exit 0
fi

# Determine template repository based on service type (sets TEMPLATE_REPO).
mscv_select_template

# Clone template repository
TEMPLATE_DIR="/tmp/template-$SERVICE_NAME"
mkdir -p $TEMPLATE_DIR
git clone https://$GITHUB_TOKEN@github.com/$GITHUB_USER/$TEMPLATE_REPO.git $TEMPLATE_DIR

# Create microservice directory and copy template
mkdir -p microservices/$SERVICE_NAME

if [ "$LANGUAGE" = "python" ] && [ "$FRAMEWORK" = "fastapi" ]; then
  mscv_scaffold_python_fastapi
elif [ "$LANGUAGE" = "rasa" ] && [ "$FRAMEWORK" = "chatbot" ]; then
  mscv_scaffold_rasa
elif [ "$LANGUAGE" = "nodejs" ] && [ "$FRAMEWORK" = "graphql-gateway" ]; then
  mscv_scaffold_nodejs_graphql
elif [ "$LANGUAGE" = "java" ] && [ "$FRAMEWORK" = "springboot" ]; then
  mscv_scaffold_java_springboot
fi

# Create service README
#
# BYTE-EQUIVALENCE NOTE (HARD-1 #168): the original inline heredoc used an
# UNQUOTED `<< EOF` with BARE (unescaped) backticks. At runtime bash performs
# command substitution on every `...` segment, so the produced README has the
# backtick contents collapsed to empty -- e.g. "Business rules ()" and empty
# Setup/Testing/Linting blocks. This is faithfully preserved below: the
# backticks are intentionally left UNESCAPED so the generated README is
# byte-identical to what the pre-extraction Job emitted. Do NOT "fix" the
# backticks -- that would change committed output for every scaffolded service.
cat > README.md << EOF
# $SERVICE_NAME

CLAUDE.md-compliant microservice with Onion Architecture and 12-Factor principles.

## Architecture

This microservice follows the Onion Architecture pattern:

- **Domain Layer**: Business rules (`src/domain/`)
- **Application Layer**: Use cases (`src/application/`)
- **Interface Layer**: REST/API endpoints (`src/interface/`)
- **Infrastructure Layer**: Database, external services (`src/infrastructure/`)

## Development

### Prerequisites
- Python 3.11+
- Poetry

### Setup
```bash
poetry install
poetry run pytest  # Run TDD tests
poetry run python src/main.py  # Run locally
```

### Testing (TDD)
```bash
poetry run pytest -v
```

### Linting
```bash
poetry run black src/
poetry run isort src/
poetry run mypy src/
```

## Deployment

This service is automatically deployed via the AppContainer CI/CD pipeline when changes are pushed to the main branch.
EOF

# Update microservices README
cd ../../
if grep -q "- (Services will be listed here as they are added)" microservices/README.md; then
  sed -i "s/- (Services will be listed here as they are added)/- $SERVICE_NAME ($LANGUAGE\/$FRAMEWORK)/" microservices/README.md
else
  echo "- $SERVICE_NAME ($LANGUAGE/$FRAMEWORK)" >> microservices/README.md
fi

# EVENT-1 (#150): the GitHub Contents-API poll loop that previously lived here
# ("Waiting for CI workflow file in remote before pushing...", 12251b4) is GONE.
# Ordering is now enforced upstream in the AppContainerClaim composition: the
# per-service ApplicationClaim Objects (which spawn this mscv Job) are only
# rendered AFTER the source-repo-setup Job has succeeded - i.e. AFTER
# .github/workflows/comprehensive-gitops.yml exists in the remote. By the time
# this Job runs the workflow file is guaranteed present, so no poll is needed.
# We keep the rebase below to land cleanly on top of the workflow-file commit
# and any sibling-service commits.
git pull --rebase origin HEAD || true

# Commit and push
git config user.name "ApplicationClaim"
git config user.email "applicationclaim@platform.local"
git add .
# Idempotent: a Crossplane Object retry can re-run this Job; skip commit if no diff.
if git diff --cached --quiet; then
  echo "no changes for $SERVICE_NAME, skipping commit"
else
  git commit -m "Add $SERVICE_NAME microservice ($LANGUAGE/$FRAMEWORK)

- Implements CLAUDE.md Onion Architecture
- Follows 12-Factor App principles
- Includes TDD test structure with pytest
- Dependency injection ready
- FastAPI with health checks
- Multi-stage Dockerfile
- Poetry for dependency management"
fi

# UNIFY-1 (#153) concurrency-safe push with bounded rebase-retry.
mscv_git_push_retry

echo "Microservice $SERVICE_NAME added to AppContainer $APP_CONTAINER successfully"
