# V1.3.2 Release Checklist

## Pre-lock checks

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[dev]'
python - <<'PY'
import ssm
print(ssm.__version__)
assert ssm.__version__ == '1.3.2'
PY
```

## Required E2E gate

```bash
chmod +x scripts/test_v13_e2e.sh
./scripts/test_v13_e2e.sh
```

Expected final line:

```text
ALL V1.3.2 E2E GATES PASSED
```

## Optional release gates

```bash
RUN_POSTGRES=1 ./scripts/test_v13_e2e.sh
RUN_DEEPSEEK_LIVE=1 ./scripts/test_v13_e2e.sh
```

## Git tag

Run only after the required E2E gate passes from a clean extracted release root:

```bash
git add .
git commit -m "Release v1.3.2 general domain foundation"
git tag -a v1.3.2 -m "SSM Framework v1.3.2 general domain foundation release"
git push origin main --follow-tags
```

## Release artifact policy

The final public release archive should exclude:

```text
venv/
.venv/
build/
dist/
*.egg-info/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.env*
```
