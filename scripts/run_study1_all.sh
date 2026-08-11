#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"

BENCH="benchmarks/ssm_bench_v2"
OUT="${1:-build/study1}"

python scripts/run_study1.py validate "$BENCH"
python scripts/run_study1.py qualify "$BENCH" "$OUT/qualification"
python scripts/run_study1.py run-arm "$BENCH" "$OUT/baseline" --arm baseline --replicates 10
python scripts/run_study1.py run-arm "$BENCH" "$OUT/control" --arm no_change_control --replicates 10
mkdir -p "$OUT/perturbations"
for mutation in requirements_drop sml_rule_drop generated_tree_drop intended_evolution; do
  python scripts/run_study1.py mutate "$OUT/baseline" "$OUT/perturbations/$mutation" --mutation "$mutation"
done
python scripts/run_study1.py analyze "$OUT/baseline" "$OUT/control" "$OUT/perturbations" "$OUT/analysis"

echo "STUDY 1 OFFLINE FORMAL PIPELINE COMPLETE"
