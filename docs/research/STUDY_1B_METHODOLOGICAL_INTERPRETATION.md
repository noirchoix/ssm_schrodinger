# Study 1B Methodological Interpretation Note

## Why the raw `REGRESSION` verdict is not a semantic-regression finding

The Study 1B strategy analysis reuses the generic SSM release-evolution assay. That assay returns `REGRESSION` when it sees a statistically material metric change that is not authorized by a ChangeIntentContract.

In the offline-versus-online strategy comparison, the only globally significant primary change was `generated_file_count`:

- offline mean: 55.0333333;
- online mean: 55.1133333;
- effect: +0.08;
- p ≈ 1.8478×10^-24.

The semantic metrics were exactly unchanged across all 300 pairs:

- requirement recall: 1.0 → 1.0;
- foundation recall: 0.8872222 → 0.8872222;
- capability recall: 1.0 → 1.0;
- semantic score: 0.9812037 → 0.9812037.

Compile success changed only from 0.6333333 to 0.63 and was non-significant.

Therefore the raw verdict means:

> the release-oriented classifier detected an unapproved structural difference.

It does **not** mean:

> DeepSeek produced a measured semantic regression.

For Study 1B, the appropriate interpretation is **structural divergence with preserved measured semantic fidelity**.

## Why `status_match_rate = 0.3667` is misleading

The offline arm uses `CONDITIONAL` for successful generation, while the online arm uses `ACCEPTED`. Exact string comparison therefore treats successful pairs as different even when both produced applications. The 110 pairs that were rejected in both arms match, yielding about 110/300 = 36.7% exact status equality.

Future analysis should normalize both taxonomies into shared outcome classes, e.g.:

- `GENERATED`;
- `BLOCKED`;
- `FAILED`.

## Recommended analyzer change for future studies

Do not change or rerun the completed Study 1B evidence. Add a post-processing strategy-comparison layer for future analyses with:

1. normalized outcome classes;
2. a strategy-specific ChangeIntent/EquivalenceContract;
3. artifact-diversity metrics separated from semantic/runtime metrics;
4. a verdict vocabulary such as `SEMANTICALLY_EQUIVALENT_WITH_STRUCTURAL_VARIANCE`, `SEMANTIC_DEGRADATION`, `RUNTIME_DEGRADATION`, and `INCONCLUSIVE`;
5. raw release-assay output retained as secondary evidence for audit.

This preserves the original preregistered evidence while improving the interpretation model for cross-strategy research.
