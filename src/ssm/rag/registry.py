from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SourceRegistry:
    """Small YAML-backed registry for docs, package guidance, and source provenance."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict[str, Any] = {}
        if self.path.exists():
            self.data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}

    def package(self, name: str) -> dict[str, Any]:
        packages = self.data.get("packages") or {}
        if not isinstance(packages, dict):
            return {}
        package = packages.get(name, {})
        return dict(package) if isinstance(package, dict) else {}

    def sources(self) -> list[dict[str, Any]]:
        sources = self.data.get("sources") or []
        if not isinstance(sources, list):
            return []
        return [dict(source) for source in sources if isinstance(source, dict)]
