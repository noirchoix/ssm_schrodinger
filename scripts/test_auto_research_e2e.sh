#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python}"
OUT="${AUTO_RESEARCH_OUT:-build/e2e_auto_research}"
rm -rf "$OUT"
mkdir -p "$OUT/baseline" "$OUT/candidate"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON_BIN" - <<'PY'
import ssm
assert ssm.__version__ == "2.6.0.dev0", ssm.__version__
print(f"runtime version: {ssm.__version__}")
PY

"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" -m compileall -q src tests

"$PYTHON_BIN" -m ssm.cli.main research-bench-validate \
  benchmarks/ssm_bench_v1/manifest.json

INTENT="benchmarks/ssm_bench_v1/intents/ssmb-005-hr-leave-approval.md"

"$PYTHON_BIN" -m ssm.cli.main research-run \
  --file "$INTENT" \
  --out "$OUT/baseline/SSMB-005/run-00" \
  --task-id ssm-bench-v1 \
  --benchmark-case-id SSMB-005 \
  --replicate-id 00 \
  --provider mock \
  --model mock \
  --scaffold-version e2e-scaffold \
  --prompt-version e2e-prompt \
  --certification-runs 2

"$PYTHON_BIN" -m ssm.cli.main research-run \
  --file "$INTENT" \
  --out "$OUT/candidate/SSMB-005/run-00" \
  --task-id ssm-bench-v1 \
  --benchmark-case-id SSMB-005 \
  --replicate-id 00 \
  --provider mock \
  --model mock \
  --scaffold-version e2e-scaffold \
  --prompt-version e2e-prompt \
  --certification-runs 2

"$PYTHON_BIN" -m ssm.cli.main evidence-check \
  "$OUT/baseline/SSMB-005/run-00/generated_app"

"$PYTHON_BIN" -m ssm.cli.main research-trace-report \
  --trace "$OUT/baseline/SSMB-005/run-00/generation_trace.jsonl" \
  --trace "$OUT/candidate/SSMB-005/run-00/generation_trace.jsonl" \
  --out "$OUT/determinism_report.json"

"$PYTHON_BIN" -m ssm.cli.main research-replay-compare \
  "$OUT/baseline/SSMB-005/run-00/generation_trace.jsonl" \
  "$OUT/candidate/SSMB-005/run-00/generation_trace.jsonl" \
  --out "$OUT/replay_comparison.json"

"$PYTHON_BIN" -m ssm.cli.main research-contract-verify \
  --contract examples/research/default_behavioural_contract.json \
  --run "$OUT/baseline/SSMB-005/run-00/generation_run.json" \
  --out "$OUT/baseline_eval_run.json" \
  --registry "$OUT/registry"

REGISTRY_ENTRY="$($PYTHON_BIN -m ssm.cli.main research-registry-add \
  "$OUT/baseline/SSMB-005/run-00/generation_run.json" \
  --registry "$OUT/registry")"
echo "$REGISTRY_ENTRY"
DIGEST="$(printf '%s' "$REGISTRY_ENTRY" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["digest"])')"
"$PYTHON_BIN" -m ssm.cli.main research-registry-verify \
  "$DIGEST" --registry "$OUT/registry"

"$PYTHON_BIN" -m ssm.cli.main research-assay \
  --baseline "$OUT/baseline" \
  --candidate "$OUT/candidate" \
  --metric compile_success \
  --metric semantic_variance_score \
  --minimum-pairs 1 \
  --out "$OUT/evolution_assay.json"

"$PYTHON_BIN" - <<PY
import json
from pathlib import Path
out = Path('$OUT')
assert json.loads((out / 'evolution_assay.json').read_text())['verdict'] == 'NO_MATERIAL_CHANGE'
assert json.loads((out / 'replay_comparison.json').read_text())['equivalent'] is True
assert json.loads((out / 'baseline_eval_run.json').read_text())['verdict'] == 'PASS'
print('AUTO RESEARCH E2E ARTIFACTS VERIFIED')
PY

echo "ALL SSM V2.6 AUTO RESEARCH GATES PASSED"
