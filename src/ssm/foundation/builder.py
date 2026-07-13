from __future__ import annotations

import json
import os
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ssm.agents.online import OnlineDraftService, OnlineDraftValidationError
from ssm.agents.settings import OnlineAgentSettings
from ssm.evidence import validate_evidence_directory
from ssm.foundation.negotiator import CapabilityNegotiator
from ssm.pipeline import SSMCompiler


class RepairTraceEvent(BaseModel):
    attempt: int
    stage: str
    status: str
    message: str = ""
    quality_gate_results: dict[str, int] = Field(default_factory=dict)


class OnlineBuildResult(BaseModel):
    status: str
    draft_path: str
    generated_path: str
    selected_domain_packs: list[str] = Field(default_factory=list)
    quality_gate_results: dict[str, int] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    repair_trace_path: str | None = None
    attempts: int = 1


class OnlineBuildService:
    """Online draft -> negotiate -> deterministic compile -> bounded repair -> gates."""

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
        repair_attempts: int | None = None,
    ) -> OnlineBuildResult:
        out = Path(out_dir)
        draft_dir = out / "foundation"
        generated_dir = out / "generated_app"
        trace_path = out / "repair_trace.json"
        draft_path = draft_dir / "project.sml.md"
        max_attempts = max(1, repair_attempts or (self.settings.llm_max_retries + 1))
        trace: list[RepairTraceEvent] = []
        last_issue = ""
        last_result: OnlineBuildResult | None = None

        for attempt in range(1, max_attempts + 1):
            repair_prompt = (
                prompt
                if not last_issue
                else f"{prompt}\n\nPrevious build issue:\n{last_issue}\nRepair the SML only."
            )
            try:
                draft = OnlineDraftService(self.settings, compiler=self.compiler).draft(
                    repair_prompt
                )
            except OnlineDraftValidationError as exc:
                last_issue = f"Online draft validation failed: {exc}"
                trace.append(
                    RepairTraceEvent(
                        attempt=attempt,
                        stage="online_draft",
                        status="rejected",
                        message=last_issue,
                    )
                )
                last_result = OnlineBuildResult(
                    status="REJECTED",
                    draft_path=str(draft_path),
                    generated_path=str(generated_dir),
                    repair_trace_path=str(trace_path),
                    attempts=attempt,
                )
                continue

            draft_dir.mkdir(parents=True, exist_ok=True)
            draft_path.write_text(draft.text, encoding="utf-8")
            negotiation = self.negotiator.negotiate_sml_text(
                draft.text,
                source_file=str(draft_path),
            )
            if negotiation.status == "UNSUPPORTED":
                last_issue = "Capability negotiation rejected the SML draft."
                trace.append(
                    RepairTraceEvent(
                        attempt=attempt,
                        stage="capability_negotiation",
                        status="rejected",
                        message=last_issue,
                    )
                )
                last_result = OnlineBuildResult(
                    status="REJECTED",
                    draft_path=str(draft_path),
                    generated_path=str(generated_dir),
                    selected_domain_packs=negotiation.selected_domain_packs,
                    assumptions=draft.assumptions,
                    unresolved_questions=draft.unresolved_questions,
                    repair_trace_path=str(trace_path),
                    attempts=attempt,
                )
                continue

            try:
                result = self.compiler.compile_text(draft.text, source_file=str(draft_path))
                if generated_dir.exists():
                    self._remove_generated_dir(generated_dir)
                self.compiler.write_result(result, generated_dir)
            except Exception as exc:
                last_issue = f"Compiler failed: {exc}"
                trace.append(
                    RepairTraceEvent(
                        attempt=attempt,
                        stage="compile",
                        status="rejected",
                        message=last_issue,
                    )
                )
                last_result = OnlineBuildResult(
                    status="REJECTED",
                    draft_path=str(draft_path),
                    generated_path=str(generated_dir),
                    selected_domain_packs=negotiation.selected_domain_packs,
                    assumptions=draft.assumptions,
                    unresolved_questions=draft.unresolved_questions,
                    repair_trace_path=str(trace_path),
                    attempts=attempt,
                )
                continue

            gate_results = self._quality_gates(generated_dir) if quality_gates else {}
            accepted = not gate_results or all(code == 0 for code in gate_results.values())
            trace.append(
                RepairTraceEvent(
                    attempt=attempt,
                    stage="quality_gates" if quality_gates else "compile",
                    status="accepted" if accepted else "rejected",
                    message=("accepted" if accepted else self._gate_failure_summary(gate_results)),
                    quality_gate_results=gate_results,
                )
            )
            last_result = OnlineBuildResult(
                status="ACCEPTED" if accepted else "REJECTED",
                draft_path=str(draft_path),
                generated_path=str(generated_dir),
                selected_domain_packs=negotiation.selected_domain_packs,
                quality_gate_results=gate_results,
                assumptions=draft.assumptions,
                unresolved_questions=draft.unresolved_questions,
                repair_trace_path=str(trace_path),
                attempts=attempt,
            )
            if accepted:
                self._write_trace(trace_path, trace, last_result)
                return last_result
            last_issue = self._gate_failure_summary(gate_results)

        if last_result is None:
            last_result = OnlineBuildResult(
                status="REJECTED",
                draft_path=str(draft_path),
                generated_path=str(generated_dir),
                repair_trace_path=str(trace_path),
                attempts=max_attempts,
            )
        self._write_trace(trace_path, trace, last_result)
        return last_result

    def _quality_gates(self, generated_dir: Path) -> dict[str, int]:
        # The online-build loop uses fast deterministic gates by default. The
        # release E2E script performs the full secondary generated-app pass,
        # including pytest and mypy, after online-build writes the app. Set
        # SSM_ONLINE_FULL_GATES=1 to include those slower gates inside the repair loop.
        commands = {
            "ruff": ["ruff", "check", "."],
            "ruff_format": ["ruff", "format", "--check", "."],
            "compileall": [sys.executable, "-m", "compileall", "app", "tests"],
            "bandit": ["bandit", "-q", "-r", "app"],
        }
        if os.getenv("SSM_ONLINE_FULL_GATES") == "1":
            commands = {
                "mypy": ["mypy", "--cache-dir", ".mypy_cache_online", "app"],
                "pytest": ["pytest", "-q"],
                **commands,
            }
        gate_log = generated_dir / ".ssm_online_quality_gates.log"
        evidence_result = validate_evidence_directory(generated_dir)
        results: dict[str, int] = {"evidence_check": 0 if evidence_result.ok else 2}
        gate_log.write_text("START evidence_check\n", encoding="utf-8")
        with gate_log.open("a", encoding="utf-8") as log:
            log.write(f"END evidence_check {results['evidence_check']}\n")
            log.flush()
            for name, command in commands.items():
                log.write(f"START {name}: {' '.join(command)}\n")
                log.flush()
                try:
                    completed = subprocess.run(  # nosec B603
                        command,
                        cwd=generated_dir,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=60,
                    )
                    results[name] = completed.returncode
                    log.write(f"END {name} {completed.returncode}\n")
                    log.flush()
                except subprocess.TimeoutExpired:
                    results[name] = 124
                    log.write(f"TIMEOUT {name} 124\n")
                    log.flush()
        return results

    def _gate_failure_summary(self, gate_results: dict[str, int]) -> str:
        failing = [name for name, code in gate_results.items() if code != 0]
        return "Quality gates failed: " + ", ".join(failing)

    def _write_trace(
        self,
        trace_path: Path,
        trace: list[RepairTraceEvent],
        result: OnlineBuildResult,
    ) -> None:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "kind": "OnlineRepairTrace",
            "final_status": result.status,
            "attempts": result.attempts,
            "events": [event.model_dump() for event in trace],
        }
        trace_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def _remove_generated_dir(self, generated_dir: Path) -> None:
        for path in sorted(generated_dir.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            else:
                path.rmdir()
        generated_dir.rmdir()

    @staticmethod
    def to_json(result: OnlineBuildResult) -> str:
        return json.dumps(result.model_dump(), indent=2, sort_keys=True)
