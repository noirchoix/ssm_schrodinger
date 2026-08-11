# Reproducibility and replication note

The bundled Study 1 formal results are a **reference execution** produced from the dev.2 source in the artifact environment (Linux, Python 3.13.5). Baseline, no-change control and all intervention arms share the same locked environment identity inside that run, so the paired comparisons are internally controlled.

For portfolio use, the strongest evidence package should additionally include an independent rerun from the locally frozen Windows dev.2 checkout. Run:

```bash
bash scripts/run_study1_all.sh build/study1_local_replication
```

Do not alter SSM-Bench v2, its oracles, the protocol, alpha, metrics, pair keys or change-intent envelope before that replication. The local result should be reported as a replication, not used to rewrite the frozen reference result.

The online DeepSeek/provider path is intentionally outside Study 1's formal statistical dataset. Its dev.2 live conformance-repair release gate is separate engineering evidence. Provider/model replication belongs in Study 2, where CanonicalSemanticContext can be held constant while online candidate-SML variance is measured explicitly.
