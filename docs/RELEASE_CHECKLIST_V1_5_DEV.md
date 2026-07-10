# V1.5.0-dev Release Checklist

Run from the framework root:

```bash
python -m venv venv
source venv/bin/activate  # or venv/Scripts/activate on Git Bash/Windows
python -m pip install -e ".[dev]"
chmod +x scripts/test_v15_e2e.sh
./scripts/test_v15_e2e.sh
```

Expected final line:

```text
ALL V1.5.0-dev E2E GATES PASSED
```

Optional gates:

```bash
RUN_POSTGRES=1 ./scripts/test_v15_e2e.sh
RUN_DEEPSEEK_LIVE=1 ./scripts/test_v15_e2e.sh
SSM_ONLINE_FULL_GATES=1 ./scripts/test_v15_e2e.sh
```

Lock only after the framework gates, generated-app gates, evidence-checks, online mock build, repair trace check, admin shell check, and secret scan all pass.
