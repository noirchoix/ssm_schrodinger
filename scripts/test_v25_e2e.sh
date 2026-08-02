#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python}"
OUT="build/e2e_v25"
rm -rf "$OUT"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" -m ruff check src tests
"$PYTHON_BIN" -m ruff format --check src tests
"$PYTHON_BIN" -m mypy --cache-dir .mypy_cache_v25 src/ssm

"$PYTHON_BIN" -m ssm.cli.main requirements \
  --file examples/intent_inputs/hr_leave_readme.md \
  --out "$OUT/requirements_ir.json"

"$PYTHON_BIN" -m ssm.cli.main collapse-plan \
  --file examples/intent_inputs/hr_leave_readme.md \
  --out "$OUT/collapse_plan.json"

"$PYTHON_BIN" -m ssm.cli.main compile-intent \
  --file examples/intent_inputs/hr_leave_readme.md \
  --out "$OUT/product" \
  --certification-runs 3

"$PYTHON_BIN" -m ssm.cli.main evidence-check "$OUT/product/generated_app"

test -f "$OUT/product/requirements_ir.json"
test -f "$OUT/product/architecture_plan.json"
test -f "$OUT/product/capability_composition.json"
test -f "$OUT/product/dependency_graph.json"
test -f "$OUT/product/artifact_diff.json"
test -f "$OUT/product/certification_report.json"
test -f "$OUT/product/build_manifest.json"

echo "ALL V2.5 SCHRODINGER COLLAPSE GATES PASSED"
