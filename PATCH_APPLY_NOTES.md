# SSM V2.0.0-dev Product-Platform Candidate

This repository is a cumulative project state, not a single-file patch. It includes the locked V1.3.2 compiler foundation, the V1.4 trust/SaaS/workflow/repair layers, the V1.5 admin-client layer, and the V2 product-platform hardening boundary.

Install and run the deterministic/local gate with:

```bash
python -m pip install -e ".[dev]"
RUN_PIP_AUDIT=0 RUN_DEEPSEEK_LIVE=0 ./scripts/test_v20_e2e.sh
```

On a network-capable release host, keep dependency audit enabled. For final external-provider certification:

```bash
RUN_DEEPSEEK_LIVE=1 ./scripts/test_v20_e2e.sh
```

Do not change the runtime version from `2.0.0.dev0` to `2.0.0` until the live forced-repair gate passes and its log is retained.
