#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export RUN_PIP_AUDIT="${RUN_PIP_AUDIT:-1}"
export RUN_POSTGRES="${RUN_POSTGRES:-0}"
export RUN_DEEPSEEK_LIVE="${RUN_DEEPSEEK_LIVE:-0}"

# Resolve project root whether this script is run from the repo root or from scripts/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ] && [ -d "$SCRIPT_DIR/src/ssm" ]; then
  PROJECT_ROOT="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../pyproject.toml" ] && [ -d "$SCRIPT_DIR/../src/ssm" ]; then
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  PROJECT_ROOT="$(pwd)"
fi
cd "$PROJECT_ROOT"

BUILD_ROOT="${BUILD_ROOT:-build/e2e}"
LOG_DIR="${LOG_DIR:-build/e2e_logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/test_v13_e2e_output_$(date +%Y%m%d_%H%M%S).txt}"

mkdir -p "$(dirname "$LOG_FILE")"
: > "$LOG_FILE"

# Save output and still show it in the terminal.
exec > >(tee -a "$LOG_FILE") 2>&1

trap 'echo ""; echo "E2E FAILED at line $LINENO"; echo "Log saved to: $LOG_FILE"' ERR

echo "============================================================"
echo "SSM V1.3.2 GENERAL DOMAIN FOUNDATION — END-TO-END TEST"
echo "============================================================"
echo "Project root: $PROJECT_ROOT"
echo "Output is being saved to: $LOG_FILE"
echo ""

if [ ! -f "pyproject.toml" ] || [ ! -d "src/ssm" ]; then
  echo "ERROR: Run this script from the framework root or from the scripts/ folder."
  echo "Expected: pyproject.toml and src/ssm"
  exit 1
fi

echo "=== 1. CREATE / ACTIVATE VENV ==="

if [ ! -d "venv" ]; then
  python -m venv venv
fi

# Git Bash / Windows
if [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
# Linux / macOS
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo "ERROR: Could not find virtualenv activation script."
  exit 1
fi

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"

export PIPAPI_PYTHON_LOCATION="$(python -c 'import sys; print(sys.executable)')"

echo ""
echo "=== 2. FRAMEWORK BASELINE QUALITY ==="

QUALITY_TARGETS=(src tests)
if [ -d "scripts" ]; then
  QUALITY_TARGETS+=(scripts)
fi

pytest --cov=ssm --cov-report=term-missing
ruff check "${QUALITY_TARGETS[@]}"
ruff format --check "${QUALITY_TARGETS[@]}"

if [ -f "scripts/secret_scan.py" ]; then
  mypy src/ssm scripts/secret_scan.py
else
  mypy src/ssm
fi

python -m compileall "${QUALITY_TARGETS[@]}"

bandit -q -r src/ssm
if [ -f "scripts/secret_scan.py" ]; then
  bandit -q scripts/secret_scan.py
fi

if [ "$RUN_PIP_AUDIT" = "1" ]; then
  pip-audit
else
  echo "Skipping pip-audit because RUN_PIP_AUDIT=0"
fi

echo ""
echo "=== 3. CLI SMOKE CHECKS ==="

python -m ssm.cli.main --help >/dev/null
python -m ssm.cli.main plan --help >/dev/null
python -m ssm.cli.main negotiate --help >/dev/null
python -m ssm.cli.main compile --help >/dev/null
python -m ssm.cli.main online-build --help >/dev/null

echo ""
echo "=== 4. APP FOUNDATION PLAN → SML → NEGOTIATE → COMPILE ==="

rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT"

python -m ssm.cli.main plan \
  --prompt "Build an HR leave approval SaaS with employees, leave requests, manager approval, leave balance rules, tenant isolation, audit logs, OpenAPI contract tests, and Docker support." \
  --emit-sml \
  --out "$BUILD_ROOT/hr_leave_foundation/project.sml.md"

python -m ssm.cli.main validate "$BUILD_ROOT/hr_leave_foundation/project.sml.md"
python -m ssm.cli.main negotiate --file "$BUILD_ROOT/hr_leave_foundation/project.sml.md"

python -m ssm.cli.main compile \
  "$BUILD_ROOT/hr_leave_foundation/project.sml.md" \
  --out "$BUILD_ROOT/hr_leave_foundation_api"

echo ""
echo "=== 5. MULTI-DOMAIN BENCHMARK VALIDATE / NEGOTIATE / COMPILE ==="

BENCHMARKS=(
  "inventory_api"
  "todo_api"
  "hr_leave_api"
  "expense_approval_api"
  "crm_pipeline_api"
  "ticketing_api"
  "school_records_api"
)

for app in "${BENCHMARKS[@]}"; do
  src="examples/${app}/project.sml.md"
  out="$BUILD_ROOT/benchmarks/${app}"

  if [ ! -f "$src" ]; then
    echo "ERROR: Missing benchmark file: $src"
    exit 1
  fi

  echo "--- Benchmark: $app ---"
  python -m ssm.cli.main validate "$src"
  python -m ssm.cli.main negotiate --file "$src"
  python -m ssm.cli.main compile "$src" --out "$out"
done

echo ""
echo "=== 6. MANUAL FULL-CRUD REGRESSION SML ==="

mkdir -p "$BUILD_ROOT/full_crud_inventory"

cat > "$BUILD_ROOT/full_crud_inventory/project.sml.md" <<'EOF'
#Project
name: FullCRUDInventoryAPI
description: FastAPI inventory API with PostgreSQL, JWT auth, product full CRUD, SKU uniqueness, OpenAPI contract tests, and Docker support.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#Capability
domain_packs: generic_crud, inventory
crud: full
relationships: basic
workflows: none
tenant: false
audit: true

#DataModel Product
fields:
  id: uuid primary
  name: string required max=120
  sku: string unique required
  quantity: int default=0

#DataModel ProductCreate
fields:
  name: string required max=120
  sku: string unique required
  quantity: int default=0

#Route ListProducts
method: GET
path: /products
auth: required
body: none
returns: Product[]

#Route CreateProduct
method: POST
path: /products
auth: required
body: ProductCreate
returns: Product

#Route GetProduct
method: GET
path: /products/{id}
auth: required
body: none
returns: Product

#Route UpdateProduct
method: PATCH
path: /products/{id}
auth: required
body: ProductCreate
returns: Product

#Route DeleteProduct
method: DELETE
path: /products/{id}
auth: required
body: none
returns: Product

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
EOF

python -m ssm.cli.main validate "$BUILD_ROOT/full_crud_inventory/project.sml.md"
python -m ssm.cli.main negotiate --file "$BUILD_ROOT/full_crud_inventory/project.sml.md"

python -m ssm.cli.main compile \
  "$BUILD_ROOT/full_crud_inventory/project.sml.md" \
  --out "$BUILD_ROOT/full_crud_inventory_api"

quality_generated_app() {
  local app_dir="$1"

  echo ""
  echo "=== GENERATED APP QUALITY: $app_dir ==="

  if [ ! -d "$app_dir" ]; then
    echo "ERROR: Missing generated app directory: $app_dir"
    exit 1
  fi

  pushd "$app_dir" >/dev/null

  python -m pip install -e ".[dev]"

  pytest
  ruff check .
  ruff format --check .
  mypy app
  python -m compileall app tests
  bandit -q -r app

  if [ "$RUN_PIP_AUDIT" = "1" ]; then
    pip-audit
  else
    echo "Skipping generated-app pip-audit because RUN_PIP_AUDIT=0"
  fi

  if [ -f "alembic.ini" ]; then
    alembic upgrade head
    alembic downgrade base
    alembic upgrade head
  else
    echo "No alembic.ini found; skipping migration cycle."
  fi

  if [ "$RUN_POSTGRES" = "1" ] && [ -f "docker-compose.yml" ] && [ -f "tests/test_postgres_integration.py" ]; then
    echo ""
    echo "=== OPTIONAL POSTGRES INTEGRATION: $app_dir ==="

    docker compose up -d db

    for i in {1..30}; do
      if docker compose exec -T db pg_isready -U app -d app; then
        break
      fi
      sleep 2
    done

    export DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/app"
    export POSTGRES_TEST_DATABASE_URL="$DATABASE_URL"
    export RUN_POSTGRES_INTEGRATION=1
    export JWT_SECRET_KEY="local-postgres-secret-key-change-me-32-bytes"
    export CREATE_DB_ON_STARTUP="false"

    alembic upgrade head
    pytest tests/test_postgres_integration.py --no-cov

    docker compose down -v
  fi

  popd >/dev/null
}

echo ""
echo "=== 7. QUALITY GATES FOR SELECTED GENERATED APPS ==="

quality_generated_app "$BUILD_ROOT/hr_leave_foundation_api"
quality_generated_app "$BUILD_ROOT/full_crud_inventory_api"
quality_generated_app "$BUILD_ROOT/benchmarks/hr_leave_api"

echo ""
echo "=== 8. ONLINE-BUILD MOCK ACCEPTANCE LOOP ==="

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
  --quality-gates

if [ -d "$BUILD_ROOT/online_mock/generated_app" ]; then
  quality_generated_app "$BUILD_ROOT/online_mock/generated_app"
elif [ -d "$BUILD_ROOT/online_mock/api" ]; then
  quality_generated_app "$BUILD_ROOT/online_mock/api"
elif [ -d "$BUILD_ROOT/online_mock/generated_api" ]; then
  quality_generated_app "$BUILD_ROOT/online_mock/generated_api"
else
  echo "Online mock build completed. No standard generated app folder found for secondary quality pass."
fi

echo ""
echo "=== 9. OPTIONAL LIVE DEEPSEEK ONLINE-BUILD ==="

if [ "$RUN_DEEPSEEK_LIVE" = "1" ]; then
  if [ -f ".env.online.local" ]; then
    set -a
    source .env.online.local
    set +a
  fi

  : "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is required when RUN_DEEPSEEK_LIVE=1}"

  export RUN_ONLINE_AI=1
  export SSM_AGENT_MODE=online
  export SSM_LLM_PROVIDER=deepseek
  export SSM_LLM_MODEL="${SSM_LLM_MODEL:-deepseek-chat}"
  export SSM_LLM_TEMPERATURE="${SSM_LLM_TEMPERATURE:-0}"
  export SSM_LLM_TIMEOUT_SECONDS="${SSM_LLM_TIMEOUT_SECONDS:-60}"
  export SSM_LLM_MAX_RETRIES="${SSM_LLM_MAX_RETRIES:-2}"
  export SSM_LLM_MAX_OUTPUT_TOKENS="${SSM_LLM_MAX_OUTPUT_TOKENS:-3000}"

  rm -rf "$BUILD_ROOT/deepseek_live"

  python -m ssm.cli.main online-build \
    --agent-mode online \
    --provider deepseek \
    --model "$SSM_LLM_MODEL" \
    --prompt "Build an HR leave approval SaaS with employees, leave requests, manager approval, leave balance rules, tenant isolation, audit logs, OpenAPI contract tests, and Docker support." \
    --out "$BUILD_ROOT/deepseek_live" \
    --quality-gates

  if [ -d "$BUILD_ROOT/deepseek_live/generated_app" ]; then
    quality_generated_app "$BUILD_ROOT/deepseek_live/generated_app"
  elif [ -d "$BUILD_ROOT/deepseek_live/api" ]; then
    quality_generated_app "$BUILD_ROOT/deepseek_live/api"
  elif [ -d "$BUILD_ROOT/deepseek_live/generated_api" ]; then
    quality_generated_app "$BUILD_ROOT/deepseek_live/generated_api"
  fi

  echo "Live DeepSeek online-build completed."
else
  echo "Skipping live DeepSeek. Set RUN_DEEPSEEK_LIVE=1 to enable."
fi

echo ""
echo "=== 10. AUDIT / SECRET CHECK ==="

find "$BUILD_ROOT" -type f | grep -Ei "audit|trace|log|jsonl" || true

if [ -f "scripts/secret_scan.py" ]; then
  # Exclude local operator files that may intentionally contain private keys.
  # Generated artifacts are still scanned.
  python scripts/secret_scan.py \
    --root . \
    --exclude .env.online.local \
    --exclude e2e_logs
else
  echo "ERROR: scripts/secret_scan.py is missing. Use the V1.3.2 hotfix package."
  exit 1
fi

echo ""
echo "============================================================"
echo "ALL V1.3.2 E2E GATES PASSED"
echo "Log saved to: $LOG_FILE"
echo "============================================================"
