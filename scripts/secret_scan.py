from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "htmlcov",
    "node_modules",
    "venv",
    ".venv",
}

# Boundary-aware token patterns. The negative lookbehind prevents false positives
# inside normal words/slugs such as "helpdesk--ticketing--api--tickets".
TOKEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("generic-sk-token", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{20,}")),
    ("google-api-key", re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_\-]{30,}")),
    ("bearer-token", re.compile(r"(?i)(?<![A-Za-z0-9])bearer\s+[A-Za-z0-9_\-.]{30,}")),
]

SECRET_ENV_NAMES = (
    "DEEPSEEK_API_KEY",
    "SSM_LLM_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "VOYAGEAI_API_KEY",
)


def iter_files(root: Path, excluded_parts: set[str], max_size: int) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in excluded_parts for part in path.parts):
            continue
        try:
            if path.stat().st_size > max_size:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Boundary-aware secret scanner for generated SSM artifacts."
    )
    parser.add_argument("--root", default=".", help="Root directory to scan.")
    parser.add_argument(
        "--max-size", type=int, default=2_000_000, help="Maximum file size to scan in bytes."
    )
    parser.add_argument(
        "--exclude", action="append", default=[], help="Additional path component to exclude."
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    excluded = set(DEFAULT_EXCLUDED_PARTS) | set(args.exclude)
    active_secret_values = [os.getenv(name) for name in SECRET_ENV_NAMES]
    active_secret_values = [value for value in active_secret_values if value]

    hits: list[tuple[str, int, str, str]] = []

    for path in iter_files(root, excluded, args.max_size):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            for secret in active_secret_values:
                if secret and secret in line:
                    hits.append(
                        (str(path.relative_to(root)), line_no, "exact-active-secret", "<redacted>")
                    )

            for label, pattern in TOKEN_PATTERNS:
                match = pattern.search(line)
                if match:
                    token = match.group(0)
                    if len(token) > 16:
                        token = token[:8] + "..." + token[-4:]
                    hits.append((str(path.relative_to(root)), line_no, label, token))

    if hits:
        print("Potential secret hits:")
        for file_name, line_no, label, token in hits:
            print(f"{file_name}:{line_no}: {label}: {token}")
        return 1

    print("No API-key-like secrets found in project files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
