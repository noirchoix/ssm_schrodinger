# Applying the V1.3.2 release-lock patch

Copy the contents of this patch over the root of your existing SSM framework folder.

Recommended sequence:

```bash
# From your project root after copying files
rm -rf src/semantic_software_markup.egg-info .pytest_cache .mypy_cache .ruff_cache build
python -m pip install -e '.[dev]'
python - <<'PY'
import ssm
print(ssm.__version__)
assert ssm.__version__ == '1.3.2'
PY
chmod +x scripts/test_v13_e2e.sh scripts/tag_v1_3_2.sh
./scripts/test_v13_e2e.sh
```

The patch contains the changed/new release-lock files only. Use the full clean release zip if you want a fresh project tree without stale caches or egg-info artifacts.
