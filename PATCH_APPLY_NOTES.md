# SSM V1.5.0-dev Platform Layer Patch

Copy these files over a clean locked V1.3.2 tree. Then run:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m pytest --cov=ssm --cov-report=term-missing -q
python -m ruff check src tests scripts
python -m ruff format --check src tests
python -m mypy src/ssm
python -m compileall src tests
python -m bandit -q -r src/ssm scripts/secret_scan.py
RUN_PIP_AUDIT=0 ./scripts/test_v15_e2e.sh
```

This is a development build, not a stable version lock.
