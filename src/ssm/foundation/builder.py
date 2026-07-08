from __future__ import annotations

import json
import subprocess  # nosec B404
import sys
from pathlib import Path

from pydantic import BaseModel, Field

from ssm.agents.online import OnlineDraftService
from ssm.agents.settings import OnlineAgentSettings
from ssm.foundation.negotiator import CapabilityNegotiator
from ssm.pipeline import SSMCompiler


class OnlineBuildResult(BaseModel):
    status: str
    draft_path: str
    generated_path: str
    selected_domain_packs: list[str] = Field(default_factory=list)
    quality_gate_results: dict[str, int] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)


class OnlineBuildService:
    """Productized online draft -> negotiate -> compile -> optional quality gates loop."""

    def __init__(self, settings: OnlineAgentSettings | None = None):
        self.settings = settings or OnlineAgentSettings.from_env()
        self.compiler = SSMCompiler()
        self.negotiator = CapabilityNegotiator()

    def build(
        self,
        *,
        prompt: str,
        out_dir: str | Path,
        quality_gates: bool = False,
    ) -> OnlineBuildResult:
        out = Path(out_dir)
        draft_dir = out / "foundation"
        generated_dir = out / "generated_app"
        draft_path = draft_dir / "project.sml.md"
        draft = OnlineDraftService(self.settings, compiler=self.compiler).draft(prompt)
        negotiation = self.negotiator.negotiate_sml_text(draft.text, source_file=str(draft_path))
        if negotiation.status == "UNSUPPORTED":
            draft_dir.mkdir(parents=True, exist_ok=True)
            draft_path.write_text(draft.text, encoding="utf-8")
            return OnlineBuildResult(
                status="REJECTED",
                draft_path=str(draft_path),
                generated_path=str(generated_dir),
                selected_domain_packs=negotiation.selected_domain_packs,
                assumptions=draft.assumptions,
                unresolved_questions=draft.unresolved_questions,
            )
        result = self.compiler.compile_text(draft.text, source_file=str(draft_path))
        draft_dir.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(draft.text, encoding="utf-8")
        self.compiler.write_result(result, generated_dir)
        gate_results = self._quality_gates(generated_dir) if quality_gates else {}
        accepted = not gate_results or all(code == 0 for code in gate_results.values())
        return OnlineBuildResult(
            status="ACCEPTED" if accepted else "REJECTED",
            draft_path=str(draft_path),
            generated_path=str(generated_dir),
            selected_domain_packs=negotiation.selected_domain_packs,
            quality_gate_results=gate_results,
            assumptions=draft.assumptions,
            unresolved_questions=draft.unresolved_questions,
        )

    def _quality_gates(self, generated_dir: Path) -> dict[str, int]:
        commands = {
            "pytest": [sys.executable, "-m", "pytest"],
            "ruff": ["ruff", "check", "."],
            "ruff_format": ["ruff", "format", "--check", "."],
            "mypy": ["mypy", "app"],
            "compileall": [sys.executable, "-m", "compileall", "app", "tests"],
            "bandit": ["bandit", "-q", "-r", "app"],
        }
        results: dict[str, int] = {}
        for name, command in commands.items():
            completed = subprocess.run(  # nosec B603
                command,
                cwd=generated_dir,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            results[name] = completed.returncode
        return results

    @staticmethod
    def to_json(result: OnlineBuildResult) -> str:
        return json.dumps(result.model_dump(), indent=2, sort_keys=True)
