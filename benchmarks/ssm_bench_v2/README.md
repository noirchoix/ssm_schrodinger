# SSM-Bench v2

SSM-Bench v2 is the frozen 30-case end-to-end benchmark used by SSM Research Study 1.

Each `cases/SSMB2-xxx/` directory contains:

- `input.md` — compiler/synthesizer input;
- `oracle.json` — evaluator-only semantic ground truth;
- `runtime_contract.json` — evaluator-only independent runtime checks;
- `metadata.json` — evaluator-only slices and case labels.

**Leakage rule:** only `input.md` may enter RequirementsIR compilation, CanonicalSemanticContext construction, offline SML rendering, or online provider synthesis. The other files are strictly post-generation evaluation material.

The benchmark is frozen by `freeze_record.json`. Current baseline semantic limitations are retained rather than editing cases to fit the implementation.
