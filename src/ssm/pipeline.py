from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ssm.backends.python_fastapi.target import PythonFastAPITarget
from ssm.frontend.parser import SMLParser
from ssm.logic.engine import LogicEngine
from ssm.logic.rules import builtin_rules
from ssm.models import CompileResult
from ssm.resolver.engine import LatentResolver
from ssm.semantic.analyzer import SemanticAnalyzer


@dataclass(frozen=True)
class CompileOptions:
    target: str = "python.fastapi"
    strict: bool = True


class SSMCompiler:
    def __init__(self, options: CompileOptions | None = None):
        self.options = options or CompileOptions()
        self.parser = SMLParser()
        self.analyzer = SemanticAnalyzer()
        self.logic = LogicEngine(builtin_rules())
        self.resolver = LatentResolver(self.logic)
        self.target = PythonFastAPITarget()
        if self.options.target != self.target.id:
            raise ValueError(f"Unsupported target in V1: {self.options.target}")

    def parse(self, sml_text: str, source_file: str = "<memory>"):
        return self.parser.parse_text(sml_text, source_file=source_file)

    def parse_file(self, path: str | Path):
        return self.parser.parse_file(path)

    def analyze_text(self, sml_text: str, source_file: str = "<memory>"):
        doc = self.parse(sml_text, source_file)
        return self.analyzer.analyze(doc)

    def compile_text(self, sml_text: str, source_file: str = "<memory>") -> CompileResult:
        doc = self.parse(sml_text, source_file)
        graph = self.analyzer.analyze(doc)
        closure = self.logic.closure(graph.facts)
        self.logic.check_required_artifacts(closure)
        resolution = self.resolver.resolve(graph)
        self.logic.check_required_artifacts(self.logic.closure(resolution.facts))
        sml_hash = self._hash_text(sml_text)
        sir_hash = self._hash_json(graph.model_dump(mode="json"))
        resolved_hash = self._hash_json(resolution.model_dump(mode="json"))
        files, manifest = self.target.generate(graph, resolution, sml_hash, sir_hash, resolved_hash)
        return CompileResult(
            success=True,
            files=files,
            manifest=manifest,
            proof_trace=resolution.proof_trace,
            sir=graph,
            resolution=resolution,
        )

    def compile_file(self, path: str | Path) -> CompileResult:
        p = Path(path)
        return self.compile_text(p.read_text(encoding="utf-8"), source_file=str(p))

    def write_result(self, result: CompileResult, out_dir: str | Path) -> None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for f in result.files:
            target = out / f.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.content, encoding="utf-8")

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _hash_json(self, payload) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
