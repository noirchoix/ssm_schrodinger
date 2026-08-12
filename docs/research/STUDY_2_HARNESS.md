# Study 2 Provenance-Locked Experiment Harness

Study 2 uses real source-level compiler mutants. Every experiment must therefore prove that Python imported the active Git worktree rather than an editable installation from another checkout.

## Invariant

Before case 1, the harness verifies and records:

- Git worktree root, branch, commit and `src/ssm` tree object;
- clean/dirty state;
- `ssm.__file__` and every declared mutant module path;
- SHA-256 of each declared mutant module;
- Python executable/version/platform and `PYTHONPATH`;
- frozen SSM-Bench v2 digest and case count.

The run aborts if the imported package/module is outside the active worktree, an expected branch/commit does not match, the benchmark fails validation, or the worktree is dirty (unless `--allow-dirty` is explicitly used for development-only preflight).

Every Study 2 `GenerationRunRecord` is re-issued content-addressedly with the provenance lock embedded in `environment.attributes`, and each replicate directory receives `source_provenance.json`.

## M-RQ-01 workflow

After applying this additive harness and validating it, commit the harness as a separate instrumentation commit on `study2/m-rq-01`. Keep the already published `study2-m-rq-01-qualified` tag on the mutation-only commit unchanged.

Set the active worktree source:

```bash
export PYTHONPATH="$PWD/src"
```

Run the fail-closed provenance gate, substituting the new harness commit SHA:

```bash
python scripts/run_study2.py provenance \
  benchmarks/ssm_bench_v2 \
  build/study2_mrq01_provenance.json \
  --mutant-id M-RQ-01 \
  --module ssm.requirements.extractor \
  --expected-branch study2/m-rq-01 \
  --expected-commit <HARNESS_COMMIT_SHA>
```

The result must have `"valid": true` and resolve both `ssm` and `ssm.requirements.extractor` under the `ssm-study2-mrq01/src/ssm` worktree.

### Provenance-locked deterministic confirmation

```bash
python scripts/run_study2.py qualify \
  benchmarks/ssm_bench_v2 \
  build/study2_mrq01_provenance_qualification \
  --baseline ../ssm_framework_v1_3_1_general_domain_foundation/build/study1_local_replication/baseline \
  --mutant-id M-RQ-01 \
  --module ssm.requirements.extractor \
  --expected-first-stage requirements \
  --expected-changed-count 8 \
  --expected-branch study2/m-rq-01 \
  --expected-commit <HARNESS_COMMIT_SHA>
```

Expected qualification evidence:

- `qualified = true`;
- assay verdict `REGRESSION`;
- causal first changed stage `requirements`;
- 8 affected cases and 22 upstream-negative controls;
- reduced independent requirement recall and semantic score;
- compile-success and generated-file-count changes are not required.

`qualification_assay.json` preserves the generic assay's raw attribution. Cross-worktree `SemanticConformanceReport` fingerprints can contain provenance-sensitive canonical-context hashes, so Study 2's causal qualification separately uses the deterministic upstream stage sequence (`requirements` through normalized canonical semantic context). Downstream verifier/target mutants must use the recorded-SML replay design rather than this direct upstream-mutant qualification path.

## M-RQ-01 online qualification

A Git worktree does not automatically receive untracked `.env.online.local`. Either copy it into the worktree without committing it or source it from the original checkout. For example:

```bash
set -a
source ../ssm_framework_v1_3_1_general_domain_foundation/.env.online.local
set +a
export SSM_LLM_API_KEY="${SSM_LLM_API_KEY:-$DEEPSEEK_API_KEY}"
```

Then run 30×1 only:

```bash
RUN_DEEPSEEK_LIVE=1 python scripts/run_study2.py online-qualify \
  benchmarks/ssm_bench_v2 \
  build/study2_mrq01_online_qualification \
  --mutant-id M-RQ-01 \
  --module ssm.requirements.extractor \
  --expected-branch study2/m-rq-01 \
  --expected-commit <HARNESS_COMMIT_SHA> \
  --provider deepseek \
  --model deepseek-chat \
  --temperature 0 \
  --max-retries 2 \
  --max-output-tokens 3000
```

Review the qualification evidence before the 30×10 run.

## Formal online mutant run

After online qualification is accepted:

```bash
RUN_DEEPSEEK_LIVE=1 python scripts/run_study2.py online-run \
  benchmarks/ssm_bench_v2 \
  build/study2_mrq01_online_repeated \
  --qualification build/study2_mrq01_online_qualification/qualification_summary.json \
  --arm study2-m-rq-01-deepseek \
  --replicates 10 \
  --mutant-id M-RQ-01 \
  --module ssm.requirements.extractor \
  --expected-branch study2/m-rq-01 \
  --expected-commit <HARNESS_COMMIT_SHA> \
  --provider deepseek \
  --model deepseek-chat \
  --temperature 0 \
  --max-retries 2 \
  --max-output-tokens 3000
```

Compare the 300 mutant observations against the frozen Study 1B online noise floor:

```bash
python scripts/run_study2.py compare-online \
  ../ssm_framework_v1_3_1_general_domain_foundation/build/study1b_online_repeated \
  build/study2_mrq01_online_repeated \
  build/study2_mrq01_online_analysis \
  --expected-first-stage requirements \
  --expected-affected-case SSMB2-002 \
  --expected-affected-case SSMB2-005 \
  --expected-affected-case SSMB2-007 \
  --expected-affected-case SSMB2-019 \
  --expected-affected-case SSMB2-020 \
  --expected-affected-case SSMB2-021 \
  --expected-affected-case SSMB2-022 \
  --expected-affected-case SSMB2-023
```

The comparison treats raw SML/SIR/generated-tree inequality as part of the Study 1B stochastic background. Primary inference is case-level (`n = 30`) and focuses on deterministic upstream causal shifts plus semantic/runtime effects.
