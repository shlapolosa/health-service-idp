#!/usr/bin/env bash
# HARD-1 (#168): lightweight dry-run harness for the mscv scaffold.
#
# Exercises the python/fastapi + realtime path with git/curl stubbed (PATH shim)
# against a tmpdir onion-template fixture. No cluster, no network, no registry.
#
# Assertions:
#   1. src/main.py written with GenericRealtimeAgent (realtime flavor)
#   2. agent_common vendored into src/agent_common/
#   3. pyproject deps appended, and idempotent on a second run (no duplicates)
#   4. push-retry loop respects the max-attempt bound (10) and exits 1 on
#      persistent rejection
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(cd "$HERE/../scripts" && pwd)"
ENTRYPOINT="$SCRIPTS_DIR/entrypoint.sh"

PASS=0; FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT

# ---------------------------------------------------------------------------
# Fixtures: a fake remote AppContainer repo, an onion template, and a fake
# health-service-idp clone (for agent_common vendoring).
# ---------------------------------------------------------------------------
APPCONTAINER_FIXTURE="$ROOT/fixtures/appcontainer"   # what `git clone <appcontainer>` yields
TEMPLATE_FIXTURE="$ROOT/fixtures/onion-template"      # what `git clone <template>` yields
HSI_FIXTURE="$ROOT/fixtures/health-service-idp"       # what the vendoring clone yields

mkdir -p "$APPCONTAINER_FIXTURE/microservices"
cat > "$APPCONTAINER_FIXTURE/microservices/README.md" <<'EOF'
# Microservices
- (Services will be listed here as they are added)
EOF

# Onion template: pyproject + a src/main.py that the realtime flavor overwrites.
mkdir -p "$TEMPLATE_FIXTURE/src"
cat > "$TEMPLATE_FIXTURE/pyproject.toml" <<'EOF'
[tool.poetry]
name = "template-service"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "*"
EOF
cat > "$TEMPLATE_FIXTURE/README.md" <<'EOF'
# Template Service
template-service onion template
EOF
echo "print('template-service placeholder')" > "$TEMPLATE_FIXTURE/src/main.py"

# Fake health-service-idp clone with agent_common package source.
AC_PKG="$HSI_FIXTURE/microservices/shared-libs/agent-common/src/agent_common"
mkdir -p "$AC_PKG"
echo "# realtime_fastapi"  > "$AC_PKG/realtime_fastapi.py"
echo "# realtime_agent"    > "$AC_PKG/realtime_agent.py"
echo "# __init__"          > "$AC_PKG/__init__.py"

# ---------------------------------------------------------------------------
# PATH shims for git / curl. Behaviour is selected via env knobs so we can
# drive both the happy path and the push-rejection path.
# ---------------------------------------------------------------------------
STUB_DIR="$ROOT/bin"
mkdir -p "$STUB_DIR"

cat > "$STUB_DIR/git" <<STUBEOF
#!/usr/bin/env bash
# Minimal git stub. Honors:
#   GIT_PUSH_MODE=ok|reject   (default ok)
#   APPCONTAINER_FIXTURE, TEMPLATE_FIXTURE, HSI_FIXTURE
case "\$1" in
  clone)
    # last arg is dest (".", a dir, or absent->repo name); resolve source by URL.
    url=""; dest="."
    shift
    args=("\$@")
    # strip flags like --depth 1
    pos=()
    skip=0
    for a in "\${args[@]}"; do
      if [ "\$skip" = "1" ]; then skip=0; continue; fi
      case "\$a" in
        --depth) skip=1;;
        --*) ;;
        *) pos+=("\$a");;
      esac
    done
    url="\${pos[0]:-}"; dest="\${pos[1]:-.}"
    src=""
    case "\$url" in
      *health-service-idp.git) src="\$HSI_FIXTURE";;
      *onion-architecture-template.git) src="\$TEMPLATE_FIXTURE";;
      *) src="\$APPCONTAINER_FIXTURE";;   # the AppContainer repo
    esac
    mkdir -p "\$dest"
    cp -r "\$src/." "\$dest/"
    exit 0
    ;;
  push)
    if [ "\${GIT_PUSH_MODE:-ok}" = "reject" ]; then
      echo "stub: push rejected (non-fast-forward)" >&2
      exit 1
    fi
    echo "stub: push ok"
    exit 0
    ;;
  config|add|commit|fetch|pull|rebase|init|checkout|remote)
    # no-op; commit prints nothing, diff handled separately
    exit 0
    ;;
  diff)
    # `git diff --cached --quiet` -> exit 1 means "there ARE changes" so we commit.
    exit 1
    ;;
  *) exit 0;;
esac
STUBEOF
chmod +x "$STUB_DIR/git"

cat > "$STUB_DIR/curl" <<'STUBEOF'
#!/usr/bin/env bash
# not exercised on the python/fastapi path; echo empty.
exit 0
STUBEOF
chmod +x "$STUB_DIR/curl"

# GNU-sed shim: the scaffold scripts assume GNU `sed -i` (the image is alpine /
# GNU sed). On a BSD-sed host (macOS) the in-place + append syntax differs, so
# we shim `sed` to a tiny Python emulator covering the exact ops the scripts use
# (s///g substitution and the GNU `/anchor/a text` append). On Linux/CI a real
# GNU sed is on PATH so this shim still works (it only needs python3).
cat > "$STUB_DIR/sed" <<'STUBEOF'
#!/usr/bin/env python3
import sys, re
args = sys.argv[1:]
in_place = False
out = []
exprs = []
files = []
i = 0
while i < len(args):
    a = args[i]
    if a == "-i":
        in_place = True
    elif a.startswith("-i") and len(a) > 2:
        in_place = True
        exprs.append(a[2:])
    elif a == "-e":
        i += 1
        exprs.append(args[i])
    elif a.startswith("-"):
        pass  # ignore other flags
    elif not exprs:
        exprs.append(a)
    else:
        files.append(a)
    i += 1

def apply_expr(text, expr):
    # split on ';' only at top level for our simple "s/a/b/g; s/c/d/g" cases.
    # The append form "/anchor/a payload" is handled whole (no ';' split).
    if re.match(r'^/.*?/a', expr) or expr.lstrip().startswith('a'):
        m = re.match(r'^/(.*?)/a\s?(.*)$', expr, re.S)
        if m:
            anchor, payload = m.group(1), m.group(2)
            payload = payload.replace('\\n', '\n')
            lines = text.split('\n')
            res = []
            for ln in lines:
                res.append(ln)
                if re.search(anchor, ln):
                    res.extend(payload.split('\n'))
            return '\n'.join(res)
    # substitution(s), possibly ';'-joined
    result = text
    for part in expr.split(';'):
        part = part.strip()
        if not part:
            continue
        sm = re.match(r'^s/(.*)$', part)
        if not sm:
            continue
        body = sm.group(1)
        # split into pat/repl/flags on unescaped '/'
        segs = re.split(r'(?<!\\)/', body)
        pat, repl = segs[0], segs[1] if len(segs) > 1 else ''
        flags = segs[2] if len(segs) > 2 else ''
        count = 0 if 'g' in flags else 1
        # GNU sed BRE-ish; our patterns are plain text so treat literally-ish
        result = re.sub(pat, repl.replace('\\/', '/'), result, count=count)
    return result

for f in files:
    with open(f) as fh:
        text = fh.read()
    had_nl = text.endswith('\n')
    body = text[:-1] if had_nl else text
    for e in exprs:
        body = apply_expr(body, e)
    body = body + ('\n' if had_nl else '')
    if in_place:
        with open(f, 'w') as fh:
            fh.write(body)
    else:
        sys.stdout.write(body)
STUBEOF
chmod +x "$STUB_DIR/sed"

export APPCONTAINER_FIXTURE TEMPLATE_FIXTURE HSI_FIXTURE

PYTHON_BIN_DIR="$(dirname "$(command -v python3)")"

run_entrypoint() {
  # Runs entrypoint.sh with stubs first on PATH, in an isolated tmp HOME.
  # python3 dir is appended so the GNU-sed shim resolves its interpreter.
  env -i \
    PATH="$STUB_DIR:/usr/bin:/bin:/usr/sbin:/sbin:$PYTHON_BIN_DIR" \
    HOME="$ROOT/home" \
    APPCONTAINER_FIXTURE="$APPCONTAINER_FIXTURE" \
    TEMPLATE_FIXTURE="$TEMPLATE_FIXTURE" \
    HSI_FIXTURE="$HSI_FIXTURE" \
    GIT_PUSH_MODE="${GIT_PUSH_MODE:-ok}" \
    SERVICE_NAME="dryrun-rt-svc" \
    APP_CONTAINER="dryrun-app" \
    LANGUAGE="python" \
    FRAMEWORK="fastapi" \
    SERVICE_FLAVOR="realtime" \
    GITHUB_TOKEN="x" \
    GITHUB_USER="dryuser" \
    bash "$ENTRYPOINT"
}

echo "=== Scenario 1: python/fastapi + realtime happy path ==="
# The entrypoint clones the AppContainer into /tmp/app-container-$APP_CONTAINER.
rm -rf "/tmp/app-container-dryrun-app" "/tmp/template-dryrun-rt-svc" || true
mkdir -p "$ROOT/home"
GIT_PUSH_MODE=ok run_entrypoint > "$ROOT/run1.log" 2>&1 || { echo "entrypoint failed:"; cat "$ROOT/run1.log"; exit 1; }

SVC_DIR="/tmp/app-container-dryrun-app/microservices/dryrun-rt-svc"

# Assertion 1: main.py with GenericRealtimeAgent
if grep -q "GenericRealtimeAgent" "$SVC_DIR/src/main.py" && grep -q "create_realtime_agent_app" "$SVC_DIR/src/main.py"; then
  ok "src/main.py written with GenericRealtimeAgent"
else
  bad "src/main.py missing GenericRealtimeAgent"
fi

# Assertion 2: agent_common vendored
if [ -f "$SVC_DIR/src/agent_common/realtime_fastapi.py" ] && [ -f "$SVC_DIR/src/agent_common/realtime_agent.py" ]; then
  ok "agent_common vendored into src/agent_common/"
else
  bad "agent_common not vendored"
fi

# Assertion 3a: pyproject deps appended
COUNT_AIOKAFKA=$(grep -c '^aiokafka' "$SVC_DIR/pyproject.toml" || true)
if [ "$COUNT_AIOKAFKA" -ge 1 ]; then
  ok "pyproject deps appended (aiokafka present)"
else
  bad "pyproject deps not appended"
fi

echo "=== Scenario 2: re-run is idempotent (no duplicate deps) ==="
# Re-run against the already-scaffolded repo (the grep -q guard should no-op).
GIT_PUSH_MODE=ok run_entrypoint > "$ROOT/run2.log" 2>&1 || { echo "rerun failed:"; cat "$ROOT/run2.log"; exit 1; }
COUNT_AIOKAFKA2=$(grep -c '^aiokafka' "$SVC_DIR/pyproject.toml" || true)
if [ "$COUNT_AIOKAFKA2" = "1" ]; then
  ok "pyproject dep injection idempotent (aiokafka count=1 after re-run)"
else
  bad "pyproject dep injection NOT idempotent (aiokafka count=$COUNT_AIOKAFKA2)"
fi

echo "=== Scenario 3: push-retry respects max attempts ==="
rm -rf "/tmp/app-container-dryrun-app" "/tmp/template-dryrun-rt-svc" || true
set +e
GIT_PUSH_MODE=reject run_entrypoint > "$ROOT/run3.log" 2>&1
RC=$?
set -e
ATTEMPTS=$(grep -c "push rejected (attempt" "$ROOT/run3.log" || true)
if [ "$RC" != "0" ] && [ "$ATTEMPTS" = "10" ] && grep -q "failed to push .* after 10 attempts" "$ROOT/run3.log"; then
  ok "push-retry bounded to 10 attempts then exit 1 (rc=$RC, attempts=$ATTEMPTS)"
else
  bad "push-retry bound wrong (rc=$RC, attempts=$ATTEMPTS)"
  echo "----- run3.log tail -----"; tail -15 "$ROOT/run3.log"
fi

echo
echo "=== RESULT: $PASS passed, $FAIL failed ==="
[ "$FAIL" = "0" ]
