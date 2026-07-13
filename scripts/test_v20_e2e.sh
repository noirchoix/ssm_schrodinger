#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export RUN_PIP_AUDIT="${RUN_PIP_AUDIT:-1}"
export RUN_DEEPSEEK_LIVE="${RUN_DEEPSEEK_LIVE:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

BUILD_ROOT="${BUILD_ROOT:-build/e2e_v20}"
LOG_DIR="${LOG_DIR:-build/e2e_logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/test_v20_e2e_output_$(date +%Y%m%d_%H%M%S).txt}"
mkdir -p "$(dirname "$LOG_FILE")"
: > "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

trap 'echo ""; echo "V2.0.0-dev E2E FAILED at line $LINENO"; echo "Log saved to: $LOG_FILE"' ERR

if [ ! -f pyproject.toml ] || [ ! -d src/ssm ]; then
  echo "ERROR: Run from the framework root or scripts/ folder."
  exit 1
fi

echo "============================================================"
echo "SSM V2.0.0-dev PRODUCT PLATFORM — END-TO-END RELEASE GATE"
echo "============================================================"
echo "Project root: $PROJECT_ROOT"
echo "Output is being saved to: $LOG_FILE"

if [ ! -d venv ]; then
  python -m venv venv
fi
if [ -f venv/Scripts/activate ]; then
  source venv/Scripts/activate
elif [ -f venv/bin/activate ]; then
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

rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT"

run_admin_gate() {
  local app_dir="$1"
  echo "=== ADMIN BUILD: $app_dir/admin ==="
  pushd "$app_dir/admin" >/dev/null
  npm install --no-audit --no-fund
  npm run typecheck
  npm run build
  test -f dist/index.html
  popd >/dev/null
}

quality_generated_app() {
  local app_dir="$1"
  echo "=== GENERATED APP QUALITY: $app_dir ==="
  test -d "$app_dir"
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
  if [ "$RUN_PIP_AUDIT" = "1" ]; then
    pip-audit
  else
    echo "Skipping generated-app pip-audit"
  fi
  if [ -f alembic.ini ]; then
    alembic upgrade head
    alembic downgrade base
    alembic upgrade head
    test -f app/db/migrations/versions/0002_platform_runtime.py
  fi
  test -f generated_app_manifest.json
  test -f app_contract.json
  test -f provenance_hashes.json
  test -f evidence_bundle.json
  test -f admin/src/App.tsx
  test -f admin/src/ResourcePage.tsx
  test -f admin/src/openapiClient.ts
  popd >/dev/null
  run_admin_gate "$app_dir"
}

echo "=== 1. FRAMEWORK QUALITY AND TRUST VALIDATION ==="
pytest --cov=ssm --cov-report=term-missing -q
ruff check src tests scripts
ruff format --check src tests scripts
mypy src/ssm scripts/secret_scan.py
python -m compileall src tests scripts
bandit -q -r src/ssm scripts/secret_scan.py
if [ "$RUN_PIP_AUDIT" = "1" ]; then pip-audit; else echo "Skipping pip-audit"; fi

echo "=== 2. PLAN / VALIDATE / NEGOTIATE / COMPILE ==="
python -m ssm.cli.main plan \
  --prompt "Build an HR leave approval SaaS with tenant isolation, RBAC, database audit persistence, workflow rules, OpenAPI contracts, Docker, and a production React admin client." \
  --emit-sml \
  --out "$BUILD_ROOT/hr_foundation/project.sml.md"
python -m ssm.cli.main validate "$BUILD_ROOT/hr_foundation/project.sml.md"
python -m ssm.cli.main negotiate --file "$BUILD_ROOT/hr_foundation/project.sml.md"
python -m ssm.cli.main compile \
  "$BUILD_ROOT/hr_foundation/project.sml.md" \
  --out "$BUILD_ROOT/hr_foundation_api"

echo "=== 3. MULTI-DOMAIN TRUST/EVIDENCE COMPILE ==="
BENCHMARKS=(inventory_api todo_api hr_leave_api expense_approval_api crm_pipeline_api ticketing_api school_records_api)
for app in "${BENCHMARKS[@]}"; do
  src="examples/${app}/project.sml.md"
  out="$BUILD_ROOT/benchmarks/${app}"
  echo "--- $app ---"
  python -m ssm.cli.main validate "$src"
  python -m ssm.cli.main negotiate --file "$src"
  python -m ssm.cli.main compile "$src" --out "$out"
  python -m ssm.cli.main evidence-check "$out"
  test -f "$out/generated_app_manifest.json"
  test -f "$out/app_contract.json"
  test -f "$out/provenance_hashes.json"
  test -f "$out/admin/package.json"
done

echo "=== 4. SQLALCHEMY SAAS / WORKFLOW / UI PRODUCT GATE ==="
quality_generated_app "$BUILD_ROOT/benchmarks/hr_leave_api"
quality_generated_app "$BUILD_ROOT/benchmarks/inventory_api"

echo "=== 5. IN-MEMORY TENANT ENFORCEMENT GATE ==="
cat > "$BUILD_ROOT/tenant_memory.sml.md" <<'EOF'
#Project
name: Tenant Memory Notes

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#Tenant
enabled: true
scope: organization

#Audit
enabled: true
events: mutation

#Role Admin
permissions:
  - read
  - write

#Role Viewer
permissions:
  - read

#DataModel Note
fields:
  id: uuid primary
  title: string unique required max=120

#DataModel NoteCreate
fields:
  title: string unique required max=120

#Route ListNotes
method: GET
path: /notes
auth: required
body: none
returns: Note[]

#Route CreateNote
method: POST
path: /notes
auth: required
body: NoteCreate
returns: Note

#Route GetNote
method: GET
path: /notes/{id}
auth: required
body: none
returns: Note

#Route UpdateNote
method: PATCH
path: /notes/{id}
auth: required
body: NoteCreate
returns: Note

#Route DeleteNote
method: DELETE
path: /notes/{id}
auth: required
body: none
returns: Note
EOF
python -m ssm.cli.main compile "$BUILD_ROOT/tenant_memory.sml.md" --out "$BUILD_ROOT/tenant_memory_app"
quality_generated_app "$BUILD_ROOT/tenant_memory_app"

echo "=== 6. BOUNDED MOCK REPAIR VALIDATION ==="
cat > "$BUILD_ROOT/repair_seed.sml.md" <<'EOF'
#Project
name: Broken Seed

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel Todo
fields:
  id: uuid primary
  title: string required max=120

#Route ListTodos
method: GET
path: /todos
auth: required
body: none
returns: Todo[]
EOF
export RUN_ONLINE_AI=1
export SSM_AGENT_MODE=online
export SSM_LLM_PROVIDER=mock
export SSM_LLM_MODEL=mock-sml-drafter
export SSM_LLM_TEMPERATURE=0
export SSM_LLM_TIMEOUT_SECONDS=60
export SSM_LLM_MAX_RETRIES=0
export SSM_LLM_MAX_OUTPUT_TOKENS=4000
python -m ssm.cli.main online-build \
  --agent-mode online \
  --provider mock \
  --model mock-sml-drafter \
  --prompt "Build a todo API with CRUD, JWT authentication, evidence records, and a generated admin client." \
  --initial-draft "$BUILD_ROOT/repair_seed.sml.md" \
  --out "$BUILD_ROOT/online_mock_repair" \
  --quality-gates \
  --repair-attempts 2
python - <<PY
import json
from pathlib import Path
trace = json.loads(Path("$BUILD_ROOT/online_mock_repair/repair_trace.json").read_text())
assert trace["schema_version"] == "2.0"
assert trace["final_status"] == "ACCEPTED"
assert trace["attempts"] == 2
assert trace["events"][0]["stage"] == "compile"
assert trace["events"][0]["status"] == "rejected"
assert trace["events"][-1]["status"] == "accepted"
print("mock repair trace: rejected attempt 1 -> accepted attempt 2")
PY
quality_generated_app "$BUILD_ROOT/online_mock_repair/generated_app"

echo "=== 7. OPTIONAL LIVE DEEPSEEK FORCED-REPAIR VALIDATION ==="
if [ "$RUN_DEEPSEEK_LIVE" = "1" ]; then
  if [ -f .env.online.local ]; then set -a; source .env.online.local; set +a; fi
  : "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is required when RUN_DEEPSEEK_LIVE=1}"
  export SSM_LLM_PROVIDER=deepseek
  export SSM_LLM_API_KEY="${SSM_LLM_API_KEY:-$DEEPSEEK_API_KEY}"
  export SSM_LLM_MODEL="${SSM_LLM_MODEL:-deepseek-chat}"
  export SSM_LLM_MAX_RETRIES=2
  python -m ssm.cli.main online-build \
    --agent-mode online \
    --provider deepseek \
    --model "$SSM_LLM_MODEL" \
    --prompt "Build an HR leave approval SaaS with tenant isolation, RBAC, database audit persistence, workflow rules, OpenAPI contracts, Docker, and a production React admin client." \
    --initial-draft "$BUILD_ROOT/repair_seed.sml.md" \
    --out "$BUILD_ROOT/deepseek_live_repair" \
    --quality-gates \
    --repair-attempts 3 | tee "$BUILD_ROOT/deepseek_live_result.json"
  python - <<PY
import json
from pathlib import Path
trace = json.loads(Path("$BUILD_ROOT/deepseek_live_repair/repair_trace.json").read_text())
assert trace["final_status"] == "ACCEPTED", trace
assert trace["attempts"] >= 2, trace
assert trace["events"][0]["status"] == "rejected", trace
assert trace["events"][-1]["status"] == "accepted", trace
print("live DeepSeek repair accepted after a forced compiler rejection")
PY
  quality_generated_app "$BUILD_ROOT/deepseek_live_repair/generated_app"
else
  echo "Skipping live DeepSeek. Set RUN_DEEPSEEK_LIVE=1 to certify the external-provider gate."
fi

echo "=== 8. SECRET AND RELEASE SUMMARY ==="
python scripts/secret_scan.py --root . --exclude .env.online.local --exclude e2e_logs
python - <<PY
import json
from pathlib import Path
summary = {
    "schema_version": "2.0",
    "kind": "V20ReleaseGateSummary",
    "status": "PASSED",
    "runtime_version": "2.0.0.dev0",
    "live_deepseek_executed": "$RUN_DEEPSEEK_LIVE" == "1",
    "gates": [
        "framework_quality",
        "trust_and_provenance",
        "multi_domain_compile",
        "tenant_repository_enforcement",
        "rbac_runtime",
        "database_audit_persistence",
        "workflow_orchestration",
        "business_rule_runtime",
        "admin_typecheck",
        "admin_production_build",
        "bounded_mock_repair",
        "secret_scan",
    ],
}
path = Path("$BUILD_ROOT/release_gate_summary.json")
path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(path)
PY

echo "============================================================"
echo "ALL V2.0.0-dev LOCAL E2E GATES PASSED"
if [ "$RUN_DEEPSEEK_LIVE" = "1" ]; then
  echo "LIVE DEEPSEEK FORCED-REPAIR GATE PASSED"
else
  echo "LIVE DEEPSEEK GATE NOT EXECUTED IN THIS RUN"
fi
echo "Log saved to: $LOG_FILE"
echo "============================================================"
