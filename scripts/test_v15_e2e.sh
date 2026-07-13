#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export RUN_PIP_AUDIT="${RUN_PIP_AUDIT:-1}"
export RUN_POSTGRES="${RUN_POSTGRES:-0}"
export RUN_DEEPSEEK_LIVE="${RUN_DEEPSEEK_LIVE:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../pyproject.toml" ]; then
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
  PROJECT_ROOT="$SCRIPT_DIR"
else
  PROJECT_ROOT="$(pwd)"
fi
cd "$PROJECT_ROOT"

BUILD_ROOT="${BUILD_ROOT:-build/e2e_v15}"
LOG_DIR="${LOG_DIR:-build/e2e_logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/test_v15_e2e_output_$(date +%Y%m%d_%H%M%S).txt}"
mkdir -p "$(dirname "$LOG_FILE")"
: > "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

trap 'echo ""; echo "V1.5 COMPATIBILITY E2E FAILED at line $LINENO"; echo "Log saved to: $LOG_FILE"' ERR

if [ ! -f "pyproject.toml" ] || [ ! -d "src/ssm" ]; then
  echo "ERROR: Run from the framework root or scripts/ folder."
  exit 1
fi

echo "============================================================"
echo "SSM V1.5 PLATFORM COMPATIBILITY SUITE — V2 RUNTIME"
echo "============================================================"
echo "Project root: $PROJECT_ROOT"
echo "Output is being saved to: $LOG_FILE"

if [ ! -d "venv" ]; then
  python -m venv venv
fi
if [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo "ERROR: Could not find virtualenv activation script."
  exit 1
fi

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
export PIPAPI_PYTHON_LOCATION="$(python -c 'import sys; print(sys.executable)')"
python - <<'PY'
import ssm
assert ssm.__version__ == "2.0.0.dev0", ssm.__version__
print(f"runtime version: {ssm.__version__}")
PY

echo "=== 1. FRAMEWORK QUALITY ==="
pytest --cov=ssm --cov-report=term-missing -q
ruff check src tests scripts
ruff format --check src tests scripts
mypy src/ssm
python -m compileall src tests scripts
bandit -q -r src/ssm scripts/secret_scan.py
if [ "$RUN_PIP_AUDIT" = "1" ]; then pip-audit; else echo "Skipping pip-audit"; fi

echo "=== 2. PLAN / VALIDATE / NEGOTIATE / COMPILE ==="
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT"
python -m ssm.cli.main plan \
  --prompt "Build an HR leave approval SaaS with employees, leave requests, manager approval, leave balance rules, tenant isolation, audit logs, workflow approval, OpenAPI contract tests, Docker support, and generated admin UI." \
  --emit-sml \
  --out "$BUILD_ROOT/hr_leave_foundation/project.sml.md"
python -m ssm.cli.main validate "$BUILD_ROOT/hr_leave_foundation/project.sml.md"
python -m ssm.cli.main negotiate --file "$BUILD_ROOT/hr_leave_foundation/project.sml.md"
python -m ssm.cli.main compile "$BUILD_ROOT/hr_leave_foundation/project.sml.md" --out "$BUILD_ROOT/hr_leave_foundation_api"

echo "=== 3. MULTI-DOMAIN BENCHMARK COMPILE ==="
BENCHMARKS=(inventory_api todo_api hr_leave_api expense_approval_api crm_pipeline_api ticketing_api school_records_api)
for app in "${BENCHMARKS[@]}"; do
  echo "--- $app ---"
  src="examples/${app}/project.sml.md"
  out="$BUILD_ROOT/benchmarks/${app}"
  python -m ssm.cli.main validate "$src"
  python -m ssm.cli.main negotiate --file "$src"
  python -m ssm.cli.main compile "$src" --out "$out"
  python -m ssm.cli.main evidence-check "$out"
  test -f "$out/generated_app_manifest.json"
  test -f "$out/app_contract.json"
  test -f "$out/evidence_bundle.json"
  test -f "$out/admin/src/App.tsx"
done

echo "=== 4. GENERATED APP QUALITY ==="
quality_generated_app() {
  local app_dir="$1"
  echo "=== GENERATED APP QUALITY: $app_dir ==="
  if [ ! -d "$app_dir" ]; then
    echo "ERROR: Missing generated app directory: $app_dir"
    exit 1
  fi
  python -m ssm.cli.main evidence-check "$app_dir"
  pushd "$app_dir" >/dev/null
  python -m pip install -e ".[dev]"
  unset PYTHONPATH || true
  mypy --cache-dir .mypy_cache_gate app
  pytest -q
  ruff check .
  ruff format --check .
  python -m compileall app tests
  bandit -q -r app
  if [ "$RUN_PIP_AUDIT" = "1" ]; then pip-audit; else echo "Skipping generated-app pip-audit"; fi
  if [ -f "alembic.ini" ]; then
    alembic upgrade head
    alembic downgrade base
    alembic upgrade head
  fi
  test -f generated_app_manifest.json
  test -f app_contract.json
  test -f evidence_bundle.json
  test -f admin/src/App.tsx
  popd >/dev/null
}

quality_generated_app "$BUILD_ROOT/hr_leave_foundation_api"
quality_generated_app "$BUILD_ROOT/benchmarks/hr_leave_api"
quality_generated_app "$BUILD_ROOT/benchmarks/inventory_api"

echo "=== 5. ONLINE-BUILD MOCK REPAIR LOOP ==="
export RUN_ONLINE_AI=1
export SSM_AGENT_MODE=online
export SSM_LLM_PROVIDER=mock
export SSM_LLM_MODEL=mock-sml-drafter
export SSM_LLM_TEMPERATURE=0
export SSM_LLM_TIMEOUT_SECONDS=60
export SSM_LLM_MAX_RETRIES=2
export SSM_LLM_MAX_OUTPUT_TOKENS=3000
rm -rf "$BUILD_ROOT/online_mock"
python -m ssm.cli.main online-build \
  --agent-mode online \
  --provider mock \
  --model mock-sml-drafter \
  --prompt "Build an HR leave approval SaaS with employees, leave requests, manager approval, leave balance rules, tenant isolation, audit logs, OpenAPI contract tests, and Docker support." \
  --out "$BUILD_ROOT/online_mock" \
  --quality-gates \
  --repair-attempts 1

test -f "$BUILD_ROOT/online_mock/repair_trace.json"
python -m ssm.cli.main evidence-check "$BUILD_ROOT/online_mock/generated_app"
quality_generated_app "$BUILD_ROOT/online_mock/generated_app"

echo "=== 6. OPTIONAL LIVE DEEPSEEK ONLINE-BUILD ==="
if [ "$RUN_DEEPSEEK_LIVE" = "1" ]; then
  if [ -f ".env.online.local" ]; then set -a; source .env.online.local; set +a; fi
  : "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is required when RUN_DEEPSEEK_LIVE=1}"

  export SSM_LLM_PROVIDER=deepseek
  export SSM_LLM_API_KEY="${SSM_LLM_API_KEY:-$DEEPSEEK_API_KEY}"
  export SSM_LLM_MODEL="${SSM_LLM_MODEL:-deepseek-chat}"

  rm -rf "$BUILD_ROOT/deepseek_live"
  mkdir -p "$BUILD_ROOT/deepseek_live"
  python -m ssm.cli.main online-build \
    --agent-mode online \
    --provider deepseek \
    --model "$SSM_LLM_MODEL" \
    --prompt "Build an HR leave approval SaaS with employees, leave requests, manager approval, leave balance rules, tenant isolation, audit logs, OpenAPI contract tests, and Docker support." \
    --out "$BUILD_ROOT/deepseek_live" \
    --quality-gates \
    --repair-attempts 2 | tee "$BUILD_ROOT/deepseek_live/online_build_result.json"

  test -f "$BUILD_ROOT/deepseek_live/repair_trace.json"
  if [ ! -d "$BUILD_ROOT/deepseek_live/generated_app" ]; then
    echo "ERROR: Live DeepSeek online-build did not generate an app. Repair trace follows:"
    cat "$BUILD_ROOT/deepseek_live/repair_trace.json"
    exit 1
  fi

  quality_generated_app "$BUILD_ROOT/deepseek_live/generated_app"
else
  echo "Skipping live DeepSeek. Set RUN_DEEPSEEK_LIVE=1 to enable."
fi

echo "=== 7. SECRET CHECK ==="
python scripts/secret_scan.py --root . --exclude .env.online.local --exclude e2e_logs

echo "============================================================"
echo "ALL V1.5 COMPATIBILITY GATES PASSED UNDER V2.0.0-dev"
echo "Log saved to: $LOG_FILE"
echo "============================================================"
