#!/usr/bin/env bash
set -euo pipefail

VERSION="1.3.2"
TAG="v${VERSION}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../pyproject.toml" ]; then
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
  PROJECT_ROOT="$SCRIPT_DIR"
else
  PROJECT_ROOT="$(pwd)"
fi
cd "$PROJECT_ROOT"

choose_python() {
  if [ -n "${PYTHON:-}" ]; then
    echo "$PYTHON"
  elif [ -x "venv/Scripts/python.exe" ]; then
    echo "venv/Scripts/python.exe"
  elif [ -x "venv/bin/python" ]; then
    echo "venv/bin/python"
  else
    echo "python"
  fi
}

PY_BIN="$(choose_python)"

echo "Project root: $PROJECT_ROOT"
echo "Using Python: $PY_BIN"

if ! "$PY_BIN" - <<'PY'
import ssm
assert ssm.__version__ == "1.3.2", f"unexpected runtime version: {ssm.__version__}"
print(f"runtime version: {ssm.__version__}")
PY
then
  echo "ssm is not importable from the selected Python. Installing editable package into that environment..."
  "$PY_BIN" -m pip install -e ".[dev]"
  "$PY_BIN" - <<'PY'
import ssm
assert ssm.__version__ == "1.3.2", f"unexpected runtime version: {ssm.__version__}"
print(f"runtime version: {ssm.__version__}")
PY
fi

git diff --check

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: This is not a Git repository. Initialize or copy into your repo before tagging."
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists. Nothing to create."
  exit 0
fi

if [ "${ALLOW_DIRTY:-0}" != "1" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working tree has uncommitted changes."
    echo "Review and commit them first, or run ALLOW_DIRTY=1 scripts/tag_v1_3_2.sh to let this script commit all changes."
    git status --short
    exit 1
  fi

  git tag -a "$TAG" -m "SSM Framework v1.3.2 general domain foundation release"
else
  git add .
  if ! git diff --cached --quiet; then
    git commit -m "Release v1.3.2 general domain foundation"
  else
    echo "No staged changes to commit."
  fi
  git tag -a "$TAG" -m "SSM Framework v1.3.2 general domain foundation release"
fi

echo "Created tag $TAG."
echo "Push with: git push origin main --follow-tags"
