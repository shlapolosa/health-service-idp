# mscv — microservice-creator image (HARD-1 #168)

Versioned, testable container that scaffolds a microservice into an AppContainer
monorepo. This is the extraction of the ~288-line bash heredoc that previously
lived inline in the `<service>-mscv` Job of
`factory/production-lines/traditional-cloud/adapters/composition/application-claim-composition.yaml`.

The composition Job now just runs this image:

```yaml
image: healthidpuaeacr.azurecr.io/mscv:v1.0.0   # pinned, never :latest
command: [/scripts/entrypoint.sh]
```

## Behaviour

**Byte-equivalent** to the pre-extraction inline script. Same template selection,
same realtime flavor (agent_common vendoring + idempotent pyproject dep
injection), same EVENT-1 (#150) ordering assumption (single rebase, no poll),
same UNIFY-1 (#153) bounded rebase-push retry, same README/commit text.

> NOTE: the generated service `README.md` intentionally has collapsed/empty
> backtick segments (e.g. `Business rules ()`). The original heredoc used an
> unquoted `<< EOF` with bare backticks, so bash command-substitutes every
> ``...`` segment at runtime. This is reproduced faithfully — see the
> byte-equivalence comment in `scripts/entrypoint.sh`. Do not "fix" it.

## Contract (env vars — identical to the Job)

| Env | Meaning |
|-----|---------|
| `SERVICE_NAME` | microservice name (= ApplicationClaim `spec.name`) |
| `APP_CONTAINER` | target monorepo (AppContainer) name |
| `LANGUAGE` | `python` \| `rasa` \| `nodejs` \| `java` |
| `FRAMEWORK` | `fastapi` \| `chatbot` \| `graphql-gateway` \| `springboot` |
| `SERVICE_FLAVOR` | `webservice` (default) \| `realtime` |
| `GITHUB_TOKEN` | PAT for clone/push (`github-credentials` secret) |
| `GITHUB_USER` | GitHub org/user (`github-credentials` secret) |
| `DOCKER_REGISTRY`, `DOCKER_USER` | present in Job env for parity; unused here |

Supported `LANGUAGE/FRAMEWORK` pairs → template repo:

| pair | template repo |
|------|---------------|
| python/fastapi | `onion-architecture-template` |
| rasa/chatbot | `chat-template` |
| nodejs/graphql-gateway | `graphql-federation-gateway-template` |
| java/springboot | `identity-service-template` |

Any other pair → `❌ Unsupported service type` + exit 1.

## Layout

```
scripts/
  entrypoint.sh            # arg/env setup, clone, dispatch, README, commit, push
  lib/
    template-select.sh     # $LANGUAGE/$FRAMEWORK -> TEMPLATE_REPO
    python-fastapi.sh      # onion scaffold + realtime flavor block
    rasa.sh                # rasa/chatbot scaffold
    nodejs-graphql.sh      # graphql federation gateway scaffold
    java-springboot.sh     # spring boot identity scaffold
    git-push-retry.sh      # UNIFY-1 bounded rebase-push retry
```

The libs are **sourced** (not exec'd) by `entrypoint.sh` so `cd`/variables
persist across them exactly as in the original single-shell heredoc. This
modular layout is also the seam RT-2 W3 will use to branch the realtime
`main.py` by role (ingest/processor/gateway) — not implemented here.

## Versioning

- `healthidpuaeacr.azurecr.io/mscv:v<semver>` — human-pinned, what the
  composition references (`mscv:v1.0.0`).
- `healthidpuaeacr.azurecr.io/mscv:<git-sha>` — immutable, per-commit.

Bump the semver in `.github/workflows/mscv-image.yml` (`MSCV_VERSION`) when you
change behaviour, and update the `image:` tag in the composition to match.

## Test locally

No cluster / no registry needed — `tests/dry-run.sh` stubs `git`/`curl` on PATH
and runs the python-fastapi + realtime path against a tmpdir onion fixture:

```bash
bash factory/production-lines/traditional-cloud/adapters/mscv-image/tests/dry-run.sh
```

Static checks:

```bash
bash -n scripts/entrypoint.sh scripts/lib/*.sh
shellcheck scripts/entrypoint.sh scripts/lib/*.sh   # if installed
```

## Ops — one-time sequencing after merge

The composition references `mscv:v1.0.0`. That tag must exist in ACR **before**
the composition change reaches the cluster, or the Job will `ImagePullBackOff`.
Order:

1. Merge this PR → CI (`mscv-image.yml`) builds+pushes `mscv:v1.0.0` and
   `mscv:<sha>` to `healthidpuaeacr.azurecr.io`.
2. Confirm the tag exists (`az acr repository show-tags -n healthidpuaeacr --repository mscv`).
3. Then let the composition change sync to the cluster.

CI builds `linux/amd64` only (the cluster is AMD64).
