#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-build/study1b_online_repeated}"
QUALIFICATION="${2:-build/study1b_online_qualification/qualification_summary.json}"
OFFLINE_BASELINE="${3:-build/study1_local_replication/baseline}"
BENCHMARK="${4:-benchmarks/ssm_bench_v2}"

# Match the certified product E2E provider-loading behavior.
# Keep secrets local: source the ignored local env file into the process
# environment without printing its contents.
if [[ -f .env.online.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.online.local
  set +a
fi

if [[ "${RUN_DEEPSEEK_LIVE:-0}" != "1" ]]; then
  echo "Study 1B live repeated run requires explicit opt-in: RUN_DEEPSEEK_LIVE=1" >&2
  exit 2
fi

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is required for live Study 1B DeepSeek execution}"
export SSM_LLM_API_KEY="${SSM_LLM_API_KEY:-$DEEPSEEK_API_KEY}"

export RUN_ONLINE_AI=1
export SSM_AGENT_MODE=online
export SSM_LLM_PROVIDER="${SSM_LLM_PROVIDER:-deepseek}"
export SSM_LLM_MODEL="${SSM_LLM_MODEL:-deepseek-chat}"
export SSM_LLM_TEMPERATURE="${SSM_LLM_TEMPERATURE:-0}"
export SSM_LLM_MAX_RETRIES="${SSM_LLM_MAX_RETRIES:-2}"
export SSM_LLM_MAX_OUTPUT_TOKENS="${SSM_LLM_MAX_OUTPUT_TOKENS:-3000}"
export SSM_AGENT_AUDIT_LOG="${SSM_AGENT_AUDIT_LOG:-$OUT/provider_audit.jsonl}"

python scripts/run_study1b.py run-arm \
  "$BENCHMARK" \
  "$OUT" \
  --qualification "$QUALIFICATION" \
  --provider "$SSM_LLM_PROVIDER" \
  --model "$SSM_LLM_MODEL" \
  --replicates 10

python scripts/run_study1b.py analyze \
  "$OFFLINE_BASELINE" \
  "$OUT" \
  "$OUT/analysis"

echo "STUDY 1B ONLINE 30x10 REPEATED PIPELINE COMPLETE"
echo "Analysis: $OUT/analysis/study1b_analysis.json"
