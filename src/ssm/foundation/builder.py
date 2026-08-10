from __future__ import annotations

import json
import os
import subprocess  # nosec B404
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ssm.agents.online import OnlineDraftService, OnlineDraftValidationError
from ssm.agents.schemas import SMLDocumentDraft
from ssm.agents.settings import OnlineAgentSettings
from ssm.auto_research.hashing import sha256_file, sha256_value
from ssm.auto_research.records import build_generation_run_record, write_generation_run_record
from ssm.auto_research.schemas import MetricObservation
from ssm.auto_research.trace import TraceRecorder
from ssm.evidence import validate_evidence_directory
from ssm.foundation.negotiator import CapabilityNegotiator
from ssm.pipeline import SSMCompiler
from ssm.product.compiler import SchrodingerProductCompiler
from ssm.product.schemas import CanonicalSemanticContext, SemanticConformanceReport
from ssm.product.semantic_context import SemanticConformanceVerifier


class RepairTraceEvent(BaseModel):
    attempt: int
    stage: str
    status: str
    message: str = ""
    quality_gate_results: dict[str, int] = Field(default_factory=dict)
    diagnostic_codes: list[str] = Field(default_factory=list)


class OnlineBuildResult(BaseModel):
    status: str
    draft_path: str
    generated_path: str
    input_path: str | None = None
    canonical_context_path: str | None = None
    semantic_conformance_path: str | None = None
    canonical_context_sha256: str | None = None
    semantic_conformance_status: str | None = None
    selected_domain_packs: list[str] = Field(default_factory=list)
    quality_gate_results: dict[str, int] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    repair_trace_path: str | None = None
    attempts: int = 1


class OnlineBuildService:
    """Canonicalize -> constrained online SML -> conformance -> compile -> repair -> gates."""

    def __init__(self, settings: OnlineAgentSettings | None = None):
        self.settings = settings or OnlineAgentSettings.from_env()
        self.compiler = SSMCompiler()
        self.negotiator = CapabilityNegotiator()
        self.product_compiler = SchrodingerProductCompiler()
        self.conformance_verifier = SemanticConformanceVerifier()

    def build(
        self,
        *,
        prompt: str,
        out_dir: str | Path,
        quality_gates: bool = False,
        repair_attempts: int | None = None,
        initial_draft_text: str | None = None,
    ) -> OnlineBuildResult:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now(UTC)
        started_monotonic = time.monotonic()
        input_path = out / "input.md"
        input_path.write_text(prompt, encoding="utf-8")
        research_trace = TraceRecorder(
            out / "generation_trace.jsonl",
            task="online-build",
            task_input={"source_sha256": sha256_value(prompt), "source_name": "input.md"},
            attrs={
                "provider": getattr(self.settings, "llm_provider", "unknown"),
                "model": getattr(self.settings, "llm_model", "unknown"),
                "synthesis_strategy": "online",
            },
        )
        draft_dir = out / "foundation"
        generated_dir = out / "generated_app"
        trace_path = out / "repair_trace.json"
        draft_path = draft_dir / "project.sml.md"
        context_path = out / "canonical_semantic_context.json"
        conformance_path = out / "semantic_conformance.json"
        max_attempts = max(1, repair_attempts or (self.settings.llm_max_retries + 1))
        trace: list[RepairTraceEvent] = []
        last_issue = ""
        last_result: OnlineBuildResult | None = None
        product_compiler = getattr(self, "product_compiler", None) or SchrodingerProductCompiler()
        conformance_verifier = (
            getattr(self, "conformance_verifier", None) or SemanticConformanceVerifier()
        )

        context = product_compiler.prepare_semantic_context(
            prompt,
            source_name="input.md",
            trace_recorder=research_trace,
        )
        self._write_canonical_artifacts(out, context)
        blocking = product_compiler.semantic_context_blocking_reasons(context)
        if blocking:
            message = "Canonical semantic context rejected before online synthesis: " + "; ".join(
                blocking
            )
            trace.append(
                RepairTraceEvent(
                    attempt=0,
                    stage="canonical_semantic_context",
                    status="rejected",
                    message=message,
                )
            )
            last_result = self._result(
                status="REJECTED",
                input_path=input_path,
                draft_path=draft_path,
                generated_dir=generated_dir,
                context_path=context_path,
                conformance_path=conformance_path,
                context=context,
                attempts=0,
                selected_domain_packs=context.negotiation.selected_domain_packs,
                assumptions=context.negotiation.assumptions,
                unresolved_questions=context.unresolved_semantics,
                repair_trace_path=trace_path,
            )
            self._write_trace(trace_path, trace, last_result)
            research_trace.set_task_output({"status": "REJECTED", "blocking": blocking})
            self._write_research_record(
                out=out,
                prompt=prompt,
                started_at=started_at,
                started_monotonic=started_monotonic,
                result=last_result,
                trace_id=research_trace.trace_id,
            )
            return last_result

        for attempt in range(1, max_attempts + 1):
            try:
                if attempt == 1 and initial_draft_text is not None:
                    draft = SMLDocumentDraft(
                        text=initial_draft_text,
                        assumptions=["Seeded initial draft for repair validation."],
                        unresolved_questions=[],
                        provenance=["seed:initial-draft"],
                    )
                    research_trace.record(
                        "branch",
                        "seeded_initial_draft",
                        input_value={
                            "attempt": attempt,
                            "canonical_context": context.semantic_fingerprint,
                        },
                        output={"sml_sha256": sha256_value(initial_draft_text)},
                    )
                else:
                    draft_service = OnlineDraftService(
                        self.settings,
                        compiler=self.compiler,
                        trace_recorder=research_trace,
                    )
                    if hasattr(draft_service, "draft_context"):
                        draft = draft_service.draft_context(
                            context,
                            repair_issue=last_issue,
                            verify_conformance=False,
                        )
                    else:
                        draft = draft_service.draft(prompt)
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
                last_result = self._result(
                    status="REJECTED",
                    input_path=input_path,
                    draft_path=draft_path,
                    generated_dir=generated_dir,
                    context_path=context_path,
                    conformance_path=conformance_path,
                    context=context,
                    attempts=attempt,
                    selected_domain_packs=context.negotiation.selected_domain_packs,
                    repair_trace_path=trace_path,
                )
                continue

            draft_dir.mkdir(parents=True, exist_ok=True)
            draft_path.write_text(draft.text, encoding="utf-8")
            conformance = conformance_verifier.verify(
                context,
                draft.text,
                source_file=str(draft_path),
            )
            self._write_json(conformance_path, conformance.model_dump(mode="json"))
            self._write_json(
                out / f"semantic_conformance_attempt_{attempt:02d}.json",
                conformance.model_dump(mode="json"),
            )
            research_trace.record(
                "memory_op",
                "semantic_conformance",
                input_value={
                    "canonical_context": context.semantic_fingerprint,
                    "candidate_sml_sha256": sha256_value(draft.text),
                    "attempt": attempt,
                },
                output={
                    "status": conformance.status,
                    "semantic_fingerprint": conformance.semantic_fingerprint,
                    "diagnostic_codes": [item.code for item in conformance.diagnostics],
                },
            )
            if not conformance.accepted:
                last_issue = conformance_verifier.format_diagnostics(conformance)
                trace.append(
                    RepairTraceEvent(
                        attempt=attempt,
                        stage="semantic_conformance",
                        status="rejected",
                        message=last_issue,
                        diagnostic_codes=[item.code for item in conformance.diagnostics],
                    )
                )
                last_result = self._result(
                    status="REJECTED",
                    input_path=input_path,
                    draft_path=draft_path,
                    generated_dir=generated_dir,
                    context_path=context_path,
                    conformance_path=conformance_path,
                    context=context,
                    conformance=conformance,
                    attempts=attempt,
                    selected_domain_packs=context.negotiation.selected_domain_packs,
                    assumptions=draft.assumptions,
                    unresolved_questions=draft.unresolved_questions,
                    repair_trace_path=trace_path,
                )
                continue

            negotiation = self.negotiator.negotiate_sml_text(
                draft.text,
                source_file=str(draft_path),
            )
            research_trace.record(
                "memory_op",
                "candidate_capability_consistency",
                input_value={
                    "sml_sha256": sha256_value(draft.text),
                    "canonical_negotiation": context.negotiation.status,
                },
                output={
                    "status": negotiation.status,
                    "selected_domain_packs": negotiation.selected_domain_packs,
                },
            )
            if negotiation.status == "UNSUPPORTED":
                last_issue = "Candidate capability consistency check rejected the SML draft."
                trace.append(
                    RepairTraceEvent(
                        attempt=attempt,
                        stage="candidate_capability_consistency",
                        status="rejected",
                        message=last_issue,
                    )
                )
                last_result = self._result(
                    status="REJECTED",
                    input_path=input_path,
                    draft_path=draft_path,
                    generated_dir=generated_dir,
                    context_path=context_path,
                    conformance_path=conformance_path,
                    context=context,
                    conformance=conformance,
                    attempts=attempt,
                    selected_domain_packs=negotiation.selected_domain_packs,
                    assumptions=draft.assumptions,
                    unresolved_questions=draft.unresolved_questions,
                    repair_trace_path=trace_path,
                )
                continue

            try:
                compile_started = time.monotonic()
                result = self.compiler.compile_text(draft.text, source_file=str(draft_path))
                sir = result.sir
                if sir is None:
                    raise RuntimeError(
                        "Deterministic compiler returned a successful result without SIR."
                    )
                research_trace.record(
                    "memory_op",
                    "sir_and_target_generation",
                    input_value={
                        "sml_sha256": sha256_value(draft.text),
                        "semantic_conformance": conformance.semantic_fingerprint,
                    },
                    output={
                        "success": result.success,
                        "generated_file_count": len(result.files),
                    },
                    duration_ms=int((time.monotonic() - compile_started) * 1000),
                )
                self._write_json(out / "sir.json", sir.model_dump(mode="json"))
                if generated_dir.exists():
                    self._remove_generated_dir(generated_dir)
                self.compiler.write_result(result, generated_dir)
            except Exception as exc:
                last_issue = f"Compiler failed after semantic conformance: {exc}"
                research_trace.record(
                    "memory_op",
                    "sir_and_target_generation",
                    input_value={"sml_sha256": sha256_value(draft.text)},
                    error=last_issue,
                )
                trace.append(
                    RepairTraceEvent(
                        attempt=attempt,
                        stage="compile",
                        status="rejected",
                        message=last_issue,
                    )
                )
                last_result = self._result(
                    status="REJECTED",
                    input_path=input_path,
                    draft_path=draft_path,
                    generated_dir=generated_dir,
                    context_path=context_path,
                    conformance_path=conformance_path,
                    context=context,
                    conformance=conformance,
                    attempts=attempt,
                    selected_domain_packs=negotiation.selected_domain_packs,
                    assumptions=draft.assumptions,
                    unresolved_questions=draft.unresolved_questions,
                    repair_trace_path=trace_path,
                )
                continue

            gate_results = self._quality_gates(generated_dir) if quality_gates else {}
            accepted = not gate_results or all(code == 0 for code in gate_results.values())
            research_trace.record(
                "tool_call",
                "generated_app_quality_gates",
                input_value={"enabled": quality_gates},
                output={"accepted": accepted, "results": gate_results},
            )
            trace.append(
                RepairTraceEvent(
                    attempt=attempt,
                    stage="quality_gates" if quality_gates else "compile",
                    status="accepted" if accepted else "rejected",
                    message=("accepted" if accepted else self._gate_failure_summary(gate_results)),
                    quality_gate_results=gate_results,
                )
            )
            last_result = self._result(
                status="ACCEPTED" if accepted else "REJECTED",
                input_path=input_path,
                draft_path=draft_path,
                generated_dir=generated_dir,
                context_path=context_path,
                conformance_path=conformance_path,
                context=context,
                conformance=conformance,
                attempts=attempt,
                selected_domain_packs=negotiation.selected_domain_packs,
                quality_gate_results=gate_results,
                assumptions=draft.assumptions,
                unresolved_questions=draft.unresolved_questions,
                repair_trace_path=trace_path,
            )
            if accepted:
                self._write_trace(trace_path, trace, last_result)
                research_trace.set_task_output(
                    {
                        "status": last_result.status,
                        "attempts": last_result.attempts,
                        "canonical_context": context.semantic_fingerprint,
                        "semantic_conformance": conformance.semantic_fingerprint,
                    }
                )
                self._write_research_record(
                    out=out,
                    prompt=prompt,
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                    result=last_result,
                    trace_id=research_trace.trace_id,
                )
                return last_result
            last_issue = self._gate_failure_summary(gate_results)

        if last_result is None:
            last_result = self._result(
                status="REJECTED",
                input_path=input_path,
                draft_path=draft_path,
                generated_dir=generated_dir,
                context_path=context_path,
                conformance_path=conformance_path,
                context=context,
                attempts=max_attempts,
                selected_domain_packs=context.negotiation.selected_domain_packs,
                repair_trace_path=trace_path,
            )
        self._write_trace(trace_path, trace, last_result)
        research_trace.set_task_output(
            {
                "status": last_result.status,
                "attempts": last_result.attempts,
                "canonical_context": context.semantic_fingerprint,
            }
        )
        self._write_research_record(
            out=out,
            prompt=prompt,
            started_at=started_at,
            started_monotonic=started_monotonic,
            result=last_result,
            trace_id=research_trace.trace_id,
        )
        return last_result

    def _write_canonical_artifacts(
        self,
        out: Path,
        context: CanonicalSemanticContext,
    ) -> None:
        self._write_json(out / "requirements_ir.json", context.requirements.model_dump(mode="json"))
        self._write_json(out / "foundation_plan.json", context.foundation.model_dump(mode="json"))
        self._write_json(
            out / "architecture_plan.json", context.architecture.model_dump(mode="json")
        )
        self._write_json(
            out / "capability_composition.json",
            context.capabilities.model_dump(mode="json"),
        )
        self._write_json(
            out / "capability_negotiation.json",
            context.negotiation.model_dump(mode="json"),
        )
        self._write_json(
            out / "canonical_semantic_context.json",
            context.model_dump(mode="json"),
        )

    def _result(
        self,
        *,
        status: str,
        input_path: Path,
        draft_path: Path,
        generated_dir: Path,
        context_path: Path,
        conformance_path: Path,
        context: CanonicalSemanticContext,
        attempts: int,
        selected_domain_packs: list[str],
        quality_gate_results: dict[str, int] | None = None,
        assumptions: list[str] | None = None,
        unresolved_questions: list[str] | None = None,
        repair_trace_path: Path | None = None,
        conformance: SemanticConformanceReport | None = None,
    ) -> OnlineBuildResult:
        return OnlineBuildResult(
            status=status,
            draft_path=str(draft_path),
            generated_path=str(generated_dir),
            input_path=str(input_path),
            canonical_context_path=str(context_path),
            semantic_conformance_path=str(conformance_path) if conformance is not None else None,
            canonical_context_sha256=context.semantic_fingerprint,
            semantic_conformance_status=conformance.status if conformance is not None else None,
            selected_domain_packs=selected_domain_packs,
            quality_gate_results=quality_gate_results or {},
            assumptions=assumptions or [],
            unresolved_questions=unresolved_questions or [],
            repair_trace_path=str(repair_trace_path) if repair_trace_path is not None else None,
            attempts=attempts,
        )

    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    def _write_research_record(
        self,
        *,
        out: Path,
        prompt: str,
        started_at: datetime,
        started_monotonic: float,
        result: OnlineBuildResult,
        trace_id: str,
    ) -> None:
        generated = Path(result.generated_path)
        generated_files = (
            [path for path in generated.rglob("*") if path.is_file()] if generated.exists() else []
        )
        draft = Path(result.draft_path)
        repair = Path(result.repair_trace_path) if result.repair_trace_path else None
        context = (
            Path(result.canonical_context_path)
            if result.canonical_context_path is not None
            else None
        )
        conformance = (
            Path(result.semantic_conformance_path)
            if result.semantic_conformance_path is not None
            else None
        )
        requirements = out / "requirements_ir.json"
        foundation = out / "foundation_plan.json"
        architecture = out / "architecture_plan.json"
        capabilities = out / "capability_composition.json"
        negotiation = out / "capability_negotiation.json"
        sir = out / "sir.json"
        stage_fingerprints = {
            "requirements": sha256_file(requirements)
            if requirements.is_file()
            else sha256_value(None),
            "foundation": sha256_file(foundation) if foundation.is_file() else sha256_value(None),
            "architecture": sha256_file(architecture)
            if architecture.is_file()
            else sha256_value(None),
            "capabilities": sha256_file(capabilities)
            if capabilities.is_file()
            else sha256_value(None),
            "negotiation": sha256_file(negotiation)
            if negotiation.is_file()
            else sha256_value(None),
            "canonical_semantic_context": sha256_file(context)
            if context is not None and context.is_file()
            else sha256_value(None),
            "sml": sha256_file(draft) if draft.is_file() else sha256_value(None),
            "semantic_conformance": sha256_file(conformance)
            if conformance is not None and conformance.is_file()
            else sha256_value(None),
            "sir": sha256_file(sir) if sir.is_file() else sha256_value(None),
            "generated_tree": sha256_value(
                {
                    path.relative_to(generated).as_posix(): sha256_file(path)
                    for path in sorted(generated_files)
                }
            ),
            "quality_gates": sha256_value(result.quality_gate_results),
            "repair_trace": sha256_file(repair)
            if repair is not None and repair.is_file()
            else sha256_value(None),
        }
        metrics = {
            "compile_success": MetricObservation(
                name="compile_success",
                value=result.status == "ACCEPTED",
                source="online_build_status",
            ),
            "generated_file_count": MetricObservation(
                name="generated_file_count",
                value=len(generated_files),
                unit="files",
                source="generated_tree",
            ),
            "repair_attempts": MetricObservation(
                name="repair_attempts",
                value=result.attempts,
                unit="attempts",
                source="repair_trace",
            ),
            "quality_gate_pass": MetricObservation(
                name="quality_gate_pass",
                value=all(code == 0 for code in result.quality_gate_results.values())
                if result.quality_gate_results
                else None,
                source="quality_gate_results" if result.quality_gate_results else None,
                measured=bool(result.quality_gate_results),
            ),
            "semantic_conformance_pass": MetricObservation(
                name="semantic_conformance_pass",
                value=result.semantic_conformance_status == "PASS"
                if result.semantic_conformance_status is not None
                else None,
                source="semantic_conformance"
                if result.semantic_conformance_status is not None
                else None,
                measured=result.semantic_conformance_status is not None,
            ),
            "token_count": MetricObservation(
                name="token_count", value=None, unit="tokens", measured=False
            ),
            "cost_usd": MetricObservation(name="cost_usd", value=None, unit="USD", measured=False),
        }
        record = build_generation_run_record(
            output=out,
            source_text=prompt,
            source_name="input.md",
            status=result.status,
            started_at=started_at,
            duration_ms=int((time.monotonic() - started_monotonic) * 1000),
            task_id="online-build",
            stage_fingerprints=stage_fingerprints,
            metrics=metrics,
            trace_ids=[trace_id],
            slices={
                "domain_pack": "+".join(sorted(result.selected_domain_packs)) or "generic",
                "provider": getattr(self.settings, "llm_provider", "unknown"),
                "workflow": "unknown",
            },
            warnings=result.unresolved_questions,
            errors=[] if result.status == "ACCEPTED" else ["Online build was rejected."],
            provider=getattr(self.settings, "llm_provider", "unknown"),
            model=getattr(self.settings, "llm_model", "unknown"),
            scaffold_version="online-build-v2-canonical-context",
        )
        write_generation_run_record(out / "generation_run.json", record)

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
            "schema_version": "2.0",
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
