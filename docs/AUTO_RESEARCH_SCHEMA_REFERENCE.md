# Auto Research Schema Reference

## GenerationRunRecord

`generation_run.json` is the canonical comparable unit. Its `record_id` is `sha256:` plus the digest of canonical JSON excluding the identity field itself.

Required identity dimensions:

- `task_id`: stable research task label;
- `benchmark_case_id`: frozen corpus case, when applicable;
- `replicate_id`: matched repeated-run index;
- `source_sha256`;
- `environment.environment_lock_sha256`.

The environment lock covers compiler version, Python version, platform, provider/model, scaffold/prompt versions, dependency-lock digest, and declared attributes.

## MetricObservation

```json
{
  "name": "build_duration_ms",
  "value": 412,
  "unit": "ms",
  "source": "monotonic_clock",
  "measured": true
}
```

Absent evidence is explicit:

```json
{
  "name": "cost_usd",
  "value": null,
  "unit": "USD",
  "source": null,
  "measured": false
}
```

A non-null unmeasured value is rejected.

## Trace JSONL

The recorder follows the Auto trace concepts:

- one header line;
- ordered spans with unique `span_id` and `seq`;
- effectful kinds: `model_call`, `tool_call`, `env_read`, `memory_op`, `branch`;
- structural `span` kind;
- at most one `task_output` line;
- strict rejection of unknown line types, duplicate IDs/sequences, invalid parents, and mismatched trace IDs.

Determinism signature:

```text
(kind, name, sha256(canonical input))
```

Classification:

- observed once: `UNWITNESSED`;
- observed at least twice, no error, one output digest: `WITNESSED_DETERMINISTIC`;
- otherwise: `WITNESSED_DIVERGENT`.

## BehaviouralContract

A contract contains metric rules with operators:

`eq`, `ne`, `lt`, `le`, `gt`, `ge`, `between`, `present`.

Evaluation is three-valued:

- `PASS`: all required and optional-present rules pass;
- `FAIL`: any required observation is absent or any rule fails;
- `UNCHECKED`: no rule fails, but an optional observation is absent.

## ChangeIntentContract

An approved contract declares:

- baseline and candidate release;
- objectives;
- protected metrics;
- accepted metric envelopes;
- affected slices;
- approval state.

A statistically material effect is `INTENDED_EVOLUTION` only when every significant metric is authorised by an approved envelope and no protected metric changes materially.

## EvolutionAssayReport

The report contains:

- four-state verdict;
- matched pair counts;
- per-metric paired effects and p-values;
- labelled-slice results;
- first-changed-stage attribution;
- explicit reasons;
- optional change-intent ID.
