from __future__ import annotations

import json
import os
import shutil
import time
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from ssm.agents.settings import OnlineAgentSettings
from ssm.auto_research.assay import compare_releases
from ssm.auto_research.hashing import sha256_value
from ssm.auto_research.records import artifact_references, environment_identity
from ssm.auto_research.schemas import GenerationRunRecord, MetricObservation
from ssm.auto_research.study1 import (
    LoadedCase,
    benchmark_digest,
    evaluate_oracle,
    execute_runtime_contract,
    load_benchmark,
    load_records,
    validate_benchmark,
)
from ssm.foundation.builder import OnlineBuildResult, OnlineBuildService
from ssm.product.compiler import SchrodingerProductCompiler

STUDY_1B_SCHEMA_VERSION = "1.0"
STUDY_1B_PROMPT_VERSION = "canonical-context-online-v1"
STUDY_1B_SCAFFOLD_VERSION = "ssm-bench-v2-study1b"
QUALIFICATION_MIN_ACCEPTANCE_RATE = 0.70
QUALIFICATION_MIN_RUNTIME_PASS_RATE = 0.80
_UPSTREAM_STAGES = [
    "requirements",
    "foundation",
    "architecture",
    "capabilities",
    "negotiation",
    "canonical_semantic_context",
]
_VARIANCE_STAGES = ["sml", "semantic_conformance", "sir", "generated_tree"]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return {str(key): value for key, value in payload.items()}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _bool_metric(name: str, value: bool | None, source: str) -> MetricObservation:
    return MetricObservation(
        name=name,
        value=value,
        source=source if value is not None else None,
        measured=value is not None,
    )


def _numeric_metric(
    name: str,
    value: int | float | None,
    *,
    source: str,
    unit: str | None = None,
) -> MetricObservation:
    return MetricObservation(
        name=name,
        value=value,
        unit=unit,
        source=source if value is not None else None,
        measured=value is not None,
    )


def _settings_for_online(
    *,
    provider: str,
    model: str | None = None,
    temperature: float | None = None,
    timeout_seconds: int | None = None,
    max_retries: int | None = None,
    max_output_tokens: int | None = None,
) -> OnlineAgentSettings:
    env = dict(os.environ)
    env["SSM_LLM_PROVIDER"] = provider
    if model is not None:
        env["SSM_LLM_MODEL"] = model
    elif provider == "deepseek" and not env.get("SSM_LLM_MODEL"):
        env["SSM_LLM_MODEL"] = "deepseek-chat"
    base = OnlineAgentSettings.from_env(env)
    values = base.model_dump()
    values["run_online_ai"] = True
    values["agent_mode"] = "online"
    if temperature is not None:
        values["llm_temperature"] = temperature
    if timeout_seconds is not None:
        values["llm_timeout_seconds"] = timeout_seconds
    if max_retries is not None:
        values["llm_max_retries"] = max_retries
    if max_output_tokens is not None:
        values["llm_max_output_tokens"] = max_output_tokens
    return OnlineAgentSettings.model_validate(values)


def require_live_opt_in(provider: str) -> None:
    """Prevent accidental paid/provider-backed 30xN runs."""
    if provider == "mock":
        return
    if provider == "deepseek" and os.getenv("RUN_DEEPSEEK_LIVE") == "1":
        return
    if os.getenv("RUN_STUDY1B_LIVE") == "1":
        return
    raise RuntimeError(
        "Live Study 1B execution is disabled. For DeepSeek set RUN_DEEPSEEK_LIVE=1; "
        "for another explicitly configured provider set RUN_STUDY1B_LIVE=1."
    )


def _settings_contract(settings: OnlineAgentSettings) -> dict[str, Any]:
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "timeout_seconds": settings.llm_timeout_seconds,
        "max_retries": settings.llm_max_retries,
        "max_output_tokens": settings.llm_max_output_tokens,
        "json_mode": settings.llm_json_mode,
    }


def _settings_digest(settings: OnlineAgentSettings) -> str:
    return sha256_value(_settings_contract(settings))


def _validate_provider_configuration(settings: OnlineAgentSettings) -> None:
    if settings.llm_provider != "mock" and not settings.llm_api_key:
        raise RuntimeError(f"Missing API key for Study 1B provider {settings.llm_provider!r}.")


def _upstream_fingerprints(context: Any) -> dict[str, str]:
    return {
        "requirements": context.requirements.semantic_fingerprint,
        "foundation": sha256_value(context.foundation.model_dump(mode="json")),
        "architecture": context.architecture.semantic_fingerprint,
        "capabilities": context.capabilities.semantic_fingerprint,
        "negotiation": sha256_value(context.negotiation.model_dump(mode="json")),
        "canonical_semantic_context": context.semantic_fingerprint,
    }


def _trace_observations(trace_path: Path) -> dict[str, Any]:
    calls = 0
    successful_calls = 0
    model_latency_ms = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    token_measurements = 0
    trace_id: str | None = None
    response_hashes: list[str] = []

    if not trace_path.is_file():
        return {
            "trace_id": None,
            "provider_invoked": False,
            "model_call_count": 0,
            "successful_model_call_count": 0,
            "model_latency_ms": 0,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "response_hashes": [],
        }

    for raw in trace_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            continue
        if payload.get("t") == "trace":
            trace_id = str(payload.get("trace_id"))
            continue
        if payload.get("t") != "span" or payload.get("kind") != "model_call":
            continue
        calls += 1
        model_latency_ms += int(payload.get("duration_ms") or 0)
        if payload.get("error") is None:
            successful_calls += 1
        output = payload.get("output")
        if not isinstance(output, dict):
            continue
        response_hash = output.get("response_sha256")
        if isinstance(response_hash, str):
            response_hashes.append(response_hash)
        usage = output.get("usage")
        if not isinstance(usage, dict):
            continue
        measured_here = False
        for key, accumulator in [
            ("input_tokens", "input"),
            ("output_tokens", "output"),
            ("total_tokens", "total"),
        ]:
            value = usage.get(key)
            if not isinstance(value, int):
                continue
            measured_here = True
            if accumulator == "input":
                input_tokens += value
            elif accumulator == "output":
                output_tokens += value
            else:
                total_tokens += value
        if measured_here:
            token_measurements += 1

    return {
        "trace_id": trace_id,
        "provider_invoked": calls > 0,
        "model_call_count": calls,
        "successful_model_call_count": successful_calls,
        "model_latency_ms": model_latency_ms,
        "input_tokens": input_tokens if token_measurements else None,
        "output_tokens": output_tokens if token_measurements else None,
        "total_tokens": total_tokens if token_measurements else None,
        "response_hashes": response_hashes,
    }


def _conformance_observations(run_dir: Path) -> dict[str, Any]:
    reports = sorted(run_dir.glob("semantic_conformance_attempt_*.json"))
    statuses: list[str] = []
    diagnostics: list[list[str]] = []
    fingerprints: list[str] = []
    for path in reports:
        payload = _read_json(path)
        statuses.append(str(payload.get("status", "UNKNOWN")))
        fingerprints.append(str(payload.get("semantic_fingerprint", "")))
        rows = payload.get("diagnostics", [])
        if isinstance(rows, list):
            diagnostics.append(
                [
                    str(item.get("code"))
                    for item in rows
                    if isinstance(item, dict) and item.get("code") is not None
                ]
            )
        else:
            diagnostics.append([])
    return {
        "attempt_count": len(reports),
        "first_status": statuses[0] if statuses else None,
        "final_status": statuses[-1] if statuses else None,
        "statuses": statuses,
        "diagnostic_codes": diagnostics,
        "fingerprints": fingerprints,
        "first_pass": statuses[0] == "PASS" if statuses else None,
        "final_pass": statuses[-1] == "PASS" if statuses else None,
        "final_diagnostic_count": len(diagnostics[-1]) if diagnostics else None,
    }


def _generated_tree_fingerprint(generated_dir: Path) -> tuple[str | None, int]:
    manifest_path = generated_dir / "generated_app_manifest.json"
    if not manifest_path.is_file():
        return None, 0
    manifest = _read_json(manifest_path)
    rows = manifest.get("generated_files", [])
    if not isinstance(rows, list):
        return None, 0
    hashes: dict[str, str] = {}
    for raw_relative in rows:
        relative = str(raw_relative)
        path = generated_dir / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            hashes[relative] = sha256_value(normalized)
        except UnicodeDecodeError:
            hashes[relative] = sha256_value(path.read_bytes().hex())
    return sha256_value(hashes), len(hashes)


def _result_error_summary(run_dir: Path, result: OnlineBuildResult | None) -> list[str]:
    if result is None or result.status == "ACCEPTED":
        return []
    trace_path = run_dir / "repair_trace.json"
    if not trace_path.is_file():
        return ["Online build was rejected."]
    payload = _read_json(trace_path)
    events = payload.get("events", [])
    messages = [
        str(item.get("message"))
        for item in events
        if isinstance(item, dict) and item.get("status") == "rejected" and item.get("message")
    ]
    return messages[-1:] or ["Online build was rejected."]


def _archive_builder_record(run_dir: Path) -> None:
    source = run_dir / "generation_run.json"
    if source.is_file():
        target = run_dir / "online_build_generation_run.json"
        if target.exists():
            target.unlink()
        source.replace(target)


def _study_record(
    *,
    case: LoadedCase,
    replicate_id: str,
    run_dir: Path,
    settings: OnlineAgentSettings,
    started_at: datetime,
    context: Any,
    oracle_eval: dict[str, Any],
    result: OnlineBuildResult | None,
    runtime: dict[str, Any] | None,
    error: str | None,
) -> GenerationRunRecord:
    trace = _trace_observations(run_dir / "generation_trace.jsonl")
    conformance = _conformance_observations(run_dir)
    stage_fingerprints = _upstream_fingerprints(context)

    draft_path = run_dir / "foundation" / "project.sml.md"
    if draft_path.is_file():
        stage_fingerprints["sml"] = sha256_value(draft_path.read_text(encoding="utf-8"))
    if conformance["fingerprints"]:
        stage_fingerprints["semantic_conformance"] = conformance["fingerprints"][-1]
    sir_path = run_dir / "sir.json"
    if sir_path.is_file():
        stage_fingerprints["sir"] = sha256_value(_read_json(sir_path))
    generated_tree, generated_count = _generated_tree_fingerprint(run_dir / "generated_app")
    if generated_tree is not None:
        stage_fingerprints["generated_tree"] = generated_tree
    if result is not None and result.quality_gate_results:
        stage_fingerprints["quality_gates"] = sha256_value(result.quality_gate_results)
    if runtime is not None and not runtime.get("skipped"):
        stage_fingerprints["runtime_contract"] = sha256_value(runtime)

    canonical_lock = bool(
        result is not None and result.canonical_context_sha256 == context.semantic_fingerprint
    )

    runtime_pass: bool | None = None
    runtime_checks: int | None = None
    if runtime is not None and not runtime.get("skipped"):
        runtime_pass = bool(runtime.get("passed"))
        checks = runtime.get("checks")
        runtime_checks = len(checks) if isinstance(checks, list) else 0

    result_status = result.status if result is not None else "ERROR"
    expected = str(case.oracle.get("expected_outcome", "GENERATABLE"))
    expected_match = (expected == "REJECTED" and result_status == "REJECTED") or (
        expected != "REJECTED" and result_status == "ACCEPTED"
    )

    metrics = {
        "compile_success": _bool_metric(
            "compile_success",
            result_status == "ACCEPTED",
            "online_build_status",
        ),
        "provider_invoked": _bool_metric(
            "provider_invoked",
            bool(trace["provider_invoked"]),
            "generation_trace",
        ),
        "model_call_count": _numeric_metric(
            "model_call_count",
            int(trace["model_call_count"]),
            source="generation_trace",
            unit="calls",
        ),
        "successful_model_call_count": _numeric_metric(
            "successful_model_call_count",
            int(trace["successful_model_call_count"]),
            source="generation_trace",
            unit="calls",
        ),
        "synthesis_attempts": _numeric_metric(
            "synthesis_attempts",
            result.attempts if result is not None else None,
            source="repair_trace",
            unit="attempts",
        ),
        "repair_rounds": _numeric_metric(
            "repair_rounds",
            max(0, result.attempts - 1) if result is not None and result.attempts > 0 else 0,
            source="repair_trace",
            unit="rounds",
        ),
        "first_candidate_conformance": _bool_metric(
            "first_candidate_conformance",
            conformance["first_pass"],
            "semantic_conformance",
        ),
        "final_candidate_conformance": _bool_metric(
            "final_candidate_conformance",
            conformance["final_pass"],
            "semantic_conformance",
        ),
        "final_conformance_diagnostic_count": _numeric_metric(
            "final_conformance_diagnostic_count",
            conformance["final_diagnostic_count"],
            source="semantic_conformance",
            unit="diagnostics",
        ),
        "canonical_context_lock": _bool_metric(
            "canonical_context_lock", canonical_lock, "canonical_semantic_context"
        ),
        "generated_file_count": _numeric_metric(
            "generated_file_count",
            generated_count,
            source="generated_app_manifest",
            unit="files",
        ),
        "runtime_contract_pass": _bool_metric(
            "runtime_contract_pass", runtime_pass, "independent_runtime_contract"
        ),
        "runtime_check_count": _numeric_metric(
            "runtime_check_count",
            runtime_checks,
            source="independent_runtime_contract",
            unit="checks",
        ),
        "expected_outcome_match": _bool_metric(
            "expected_outcome_match", expected_match, "independent_oracle"
        ),
        "oracle_requirement_recall": _numeric_metric(
            "oracle_requirement_recall",
            float(oracle_eval["requirement_obligation_recall"]),
            source="independent_oracle",
        ),
        "oracle_foundation_recall": _numeric_metric(
            "oracle_foundation_recall",
            float(oracle_eval["foundation_obligation_recall"]),
            source="independent_oracle",
        ),
        "oracle_capability_recall": _numeric_metric(
            "oracle_capability_recall",
            float(oracle_eval["capability_obligation_recall"]),
            source="independent_oracle",
        ),
        "oracle_semantic_score": _numeric_metric(
            "oracle_semantic_score",
            float(oracle_eval["semantic_oracle_score"]),
            source="independent_oracle",
        ),
        "model_latency_ms": _numeric_metric(
            "model_latency_ms",
            int(trace["model_latency_ms"]) if trace["provider_invoked"] else None,
            source="generation_trace",
            unit="ms",
        ),
        "input_tokens": _numeric_metric(
            "input_tokens",
            trace["input_tokens"],
            source="provider_usage",
            unit="tokens",
        ),
        "output_tokens": _numeric_metric(
            "output_tokens",
            trace["output_tokens"],
            source="provider_usage",
            unit="tokens",
        ),
        "total_tokens": _numeric_metric(
            "total_tokens",
            trace["total_tokens"],
            source="provider_usage",
            unit="tokens",
        ),
        "cost_usd": MetricObservation(name="cost_usd", value=None, unit="USD", measured=False),
    }
    if result is not None and result.quality_gate_results:
        metrics["quality_gate_pass"] = _bool_metric(
            "quality_gate_pass",
            all(code == 0 for code in result.quality_gate_results.values()),
            "online_quality_gates",
        )
    else:
        metrics["quality_gate_pass"] = _bool_metric(
            "quality_gate_pass", None, "online_quality_gates"
        )

    status = result_status if result_status in {"ACCEPTED", "CONDITIONAL", "REJECTED"} else "ERROR"
    warnings = list(result.unresolved_questions) if result is not None else []
    errors = [error] if error else _result_error_summary(run_dir, result)
    trace_ids = [str(trace["trace_id"])] if trace["trace_id"] else []

    return GenerationRunRecord.create(
        run_id=f"study1b-{case.case_id}-{replicate_id}",
        task_id=case.case_id,
        benchmark_case_id=case.case_id,
        replicate_id=replicate_id,
        started_at=started_at.isoformat(),
        completed_at=datetime.now(UTC).isoformat(),
        status=status,
        reproducibility="UNKNOWN",
        source_name=str(case.input_path),
        source_sha256=sha256_value(case.input_path.read_text(encoding="utf-8")),
        environment=environment_identity(
            run_dir,
            provider=settings.llm_provider,
            model=settings.llm_model,
            scaffold_version=STUDY_1B_SCAFFOLD_VERSION,
            prompt_version=STUDY_1B_PROMPT_VERSION,
            attributes={
                "generation_strategy": "online",
                "temperature": str(settings.llm_temperature),
                "settings_sha256": _settings_digest(settings),
                "study": "1B",
            },
        ),
        stage_fingerprints=stage_fingerprints,
        metrics=metrics,
        artifacts=artifact_references(run_dir, exclude={"generation_run.json"}),
        trace_ids=trace_ids,
        eval_run_ids=[],
        slices={
            **{str(k): str(v) for k, v in case.metadata.get("slices", {}).items()},
            "generation_strategy": "online",
            "provider": settings.llm_provider,
        },
        warnings=warnings,
        errors=errors,
    )


def observe_online_case(
    case: LoadedCase,
    replicate_id: str,
    out_dir: str | Path,
    *,
    settings: OnlineAgentSettings,
    quality_gates: bool = False,
    repair_attempts: int | None = None,
) -> tuple[GenerationRunRecord, dict[str, Any]]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    text = case.input_path.read_text(encoding="utf-8")
    product = SchrodingerProductCompiler()
    context = product.prepare_semantic_context(text, source_name="input.md")
    oracle_eval = evaluate_oracle(context, case.oracle)
    blocking = product.semantic_context_blocking_reasons(context)
    started_at = datetime.now(UTC)
    result: OnlineBuildResult | None = None
    runtime: dict[str, Any] | None = None
    error: str | None = None

    try:
        result = OnlineBuildService(settings).build(
            prompt=text,
            out_dir=run_dir,
            quality_gates=quality_gates,
            repair_attempts=repair_attempts,
        )
        if result.status == "ACCEPTED" and Path(result.generated_path).exists():
            runtime = execute_runtime_contract(
                Path(result.generated_path), case.runtime_contract_path
            )
        else:
            runtime = {
                "passed": case.runtime_contract.get("mode") == "skip",
                "skipped": True,
                "reason": "No accepted generated application.",
            }
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        runtime = {
            "passed": False,
            "skipped": True,
            "reason": "Online observation raised before runtime evaluation.",
        }

    _write_json(run_dir / "oracle_evaluation.json", oracle_eval)
    _write_json(run_dir / "runtime_contract_result.json", runtime or {})
    _write_json(
        run_dir / "study1b_context_lock.json",
        {
            "expected_canonical_context_sha256": context.semantic_fingerprint,
            "observed_canonical_context_sha256": (
                result.canonical_context_sha256 if result is not None else None
            ),
            "blocking": blocking,
        },
    )
    _archive_builder_record(run_dir)
    record = _study_record(
        case=case,
        replicate_id=replicate_id,
        run_dir=run_dir,
        settings=settings,
        started_at=started_at,
        context=context,
        oracle_eval=oracle_eval,
        result=result,
        runtime=runtime,
        error=error,
    )
    (run_dir / "generation_run.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    trace = _trace_observations(run_dir / "generation_trace.jsonl")
    conformance = _conformance_observations(run_dir)
    observation = {
        "case_id": case.case_id,
        "replicate_id": replicate_id,
        "status": record.status,
        "expected_outcome": case.oracle.get("expected_outcome"),
        "blocking": blocking,
        "provider_invoked": trace["provider_invoked"],
        "model_call_count": trace["model_call_count"],
        "attempts": result.attempts if result is not None else None,
        "first_candidate_conformance": conformance["first_status"],
        "final_candidate_conformance": conformance["final_status"],
        "runtime": runtime,
        "canonical_context_expected": context.semantic_fingerprint,
        "canonical_context_observed": result.canonical_context_sha256 if result else None,
        "canonical_context_lock": bool(
            result is not None and result.canonical_context_sha256 == context.semantic_fingerprint
        ),
        "oracle": oracle_eval,
        "error": error,
    }
    _write_json(run_dir / "study1b_observation.json", observation)
    return record, observation


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _qualification_summary(
    *,
    benchmark_root: str | Path,
    settings: OnlineAgentSettings,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    provider_invoked = [item for item in observations if item.get("provider_invoked")]
    blocked = [item for item in observations if item.get("blocking")]
    accepted = [item for item in provider_invoked if item.get("status") == "ACCEPTED"]
    runtime_executed = [
        item
        for item in observations
        if isinstance(item.get("runtime"), dict) and not item["runtime"].get("skipped")
    ]
    runtime_passes = [item for item in runtime_executed if item["runtime"].get("passed")]
    infrastructure_errors = [item for item in observations if item.get("error")]
    lock_failures = [item for item in observations if not item.get("canonical_context_lock")]
    unexpected_blocked_calls = [item for item in blocked if item.get("provider_invoked")]
    first_passes = [
        item for item in provider_invoked if item.get("first_candidate_conformance") == "PASS"
    ]
    final_passes = [
        item for item in provider_invoked if item.get("final_candidate_conformance") == "PASS"
    ]
    repaired = [
        item
        for item in provider_invoked
        if isinstance(item.get("attempts"), int) and int(item["attempts"]) > 1
    ]

    acceptance_rate = _rate(len(accepted), len(provider_invoked))
    runtime_pass_rate = _rate(len(runtime_passes), len(runtime_executed))
    structural_clean = (
        not infrastructure_errors
        and not lock_failures
        and not unexpected_blocked_calls
        and bool(provider_invoked)
    )
    performance_ready = (
        acceptance_rate is not None
        and acceptance_rate >= QUALIFICATION_MIN_ACCEPTANCE_RATE
        and (runtime_pass_rate is None or runtime_pass_rate >= QUALIFICATION_MIN_RUNTIME_PASS_RATE)
    )
    return {
        "kind": "Study1BOnlineQualification",
        "schema_version": STUDY_1B_SCHEMA_VERSION,
        "benchmark_digest": benchmark_digest(benchmark_root),
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "settings": _settings_contract(settings),
        "settings_sha256": _settings_digest(settings),
        "case_count": len(observations),
        "provider_invoked_cases": len(provider_invoked),
        "upstream_fail_closed_cases": len(blocked),
        "accepted_cases": len(accepted),
        "acceptance_rate": acceptance_rate,
        "first_pass_conformance_rate": _rate(len(first_passes), len(provider_invoked)),
        "final_conformance_rate": _rate(len(final_passes), len(provider_invoked)),
        "repair_required_cases": len(repaired),
        "runtime_executed": len(runtime_executed),
        "runtime_passes": len(runtime_passes),
        "runtime_pass_rate": runtime_pass_rate,
        "infrastructure_errors": len(infrastructure_errors),
        "canonical_context_lock_failures": len(lock_failures),
        "unexpected_provider_calls_on_blocked_cases": len(unexpected_blocked_calls),
        "structural_clean": structural_clean,
        "minimum_acceptance_rate": QUALIFICATION_MIN_ACCEPTANCE_RATE,
        "minimum_runtime_pass_rate": QUALIFICATION_MIN_RUNTIME_PASS_RATE,
        "performance_ready": performance_ready,
        "ready_for_repeated_run": structural_clean and performance_ready,
        "observations": observations,
    }


def qualify_online_benchmark(
    root: str | Path,
    out_dir: str | Path,
    *,
    settings: OnlineAgentSettings,
    quality_gates: bool = True,
    repair_attempts: int | None = None,
) -> dict[str, Any]:
    validation = validate_benchmark(root)
    if not validation["valid"]:
        raise ValueError("Benchmark validation failed: " + "; ".join(validation["errors"]))
    require_live_opt_in(settings.llm_provider)
    _validate_provider_configuration(settings)
    _, cases = load_benchmark(root)
    output = Path(out_dir)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    observations: list[dict[str, Any]] = []
    for case in cases:
        _, observation = observe_online_case(
            case,
            "Q0",
            output / case.case_id / "Q0",
            settings=settings,
            quality_gates=quality_gates,
            repair_attempts=repair_attempts,
        )
        observations.append(observation)
        summary = _qualification_summary(
            benchmark_root=root,
            settings=settings,
            observations=observations,
        )
        _write_json(output / "qualification_summary.partial.json", summary)

    summary = _qualification_summary(
        benchmark_root=root,
        settings=settings,
        observations=observations,
    )
    _write_json(output / "qualification_summary.json", summary)
    partial = output / "qualification_summary.partial.json"
    if partial.exists():
        partial.unlink()
    return summary


def _validate_qualification_gate(
    qualification_path: str | Path,
    *,
    benchmark_root: str | Path,
    settings: OnlineAgentSettings,
) -> dict[str, Any]:
    summary = _read_json(Path(qualification_path))
    if summary.get("kind") != "Study1BOnlineQualification":
        raise ValueError("Qualification file is not a Study1BOnlineQualification record.")
    if summary.get("benchmark_digest") != benchmark_digest(benchmark_root):
        raise ValueError("Qualification benchmark digest does not match the frozen benchmark.")
    if (
        summary.get("provider") != settings.llm_provider
        or summary.get("model") != settings.llm_model
    ):
        raise ValueError("Qualification provider/model does not match repeated-run settings.")
    if summary.get("settings_sha256") != _settings_digest(settings):
        raise ValueError("Qualification online settings do not match repeated-run settings.")
    if not summary.get("ready_for_repeated_run"):
        raise ValueError(
            "Study 1B qualification is not ready for the repeated run. Review qualification_summary.json."
        )
    return summary


def _arm_summary(
    records: Iterable[GenerationRunRecord], *, arm: str, replicates: int
) -> dict[str, Any]:
    rows = list(records)
    provider_invoked = sum(bool(item.metrics["provider_invoked"].value) for item in rows)
    accepted = sum(item.status == "ACCEPTED" for item in rows)
    runtime_measured = [item for item in rows if item.metrics["runtime_contract_pass"].measured]
    runtime_passes = sum(
        bool(item.metrics["runtime_contract_pass"].value) for item in runtime_measured
    )
    return {
        "kind": "Study1BRepeatedArm",
        "schema_version": STUDY_1B_SCHEMA_VERSION,
        "arm": arm,
        "records": len(rows),
        "replicates": replicates,
        "status_counts": dict(Counter(item.status for item in rows)),
        "provider_invoked_records": provider_invoked,
        "accepted_records": accepted,
        "acceptance_rate_when_invoked": _rate(accepted, provider_invoked),
        "runtime_measured_records": len(runtime_measured),
        "runtime_passes": runtime_passes,
        "runtime_pass_rate": _rate(runtime_passes, len(runtime_measured)),
        "mean_total_tokens": _metric_mean(rows, "total_tokens"),
        "mean_model_latency_ms": _metric_mean(rows, "model_latency_ms"),
    }


def run_online_repeated_arm(
    root: str | Path,
    out_dir: str | Path,
    *,
    settings: OnlineAgentSettings,
    qualification_path: str | Path,
    arm: str = "deepseek_online",
    replicates: int = 10,
    quality_gates: bool = False,
    repair_attempts: int | None = None,
    delay_seconds: float = 0.0,
    resume: bool = True,
) -> dict[str, Any]:
    validation = validate_benchmark(root)
    if not validation["valid"]:
        raise ValueError("Benchmark validation failed: " + "; ".join(validation["errors"]))
    require_live_opt_in(settings.llm_provider)
    _validate_provider_configuration(settings)
    _validate_qualification_gate(
        qualification_path,
        benchmark_root=root,
        settings=settings,
    )
    _, cases = load_benchmark(root)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    records: list[GenerationRunRecord] = []

    for case in cases:
        for index in range(replicates):
            replicate_id = f"R{index:02d}"
            run_dir = output / case.case_id / replicate_id
            record_path = run_dir / "generation_run.json"
            if resume and record_path.is_file():
                existing = GenerationRunRecord.model_validate_json(
                    record_path.read_text(encoding="utf-8")
                )
                if existing.verify_identity():
                    existing_settings = existing.environment.attributes.get("settings_sha256")
                    if existing_settings != _settings_digest(settings):
                        raise ValueError(
                            f"Existing observation {record_path} was created with different online settings."
                        )
                    records.append(existing)
                    continue
            record, observation = observe_online_case(
                case,
                replicate_id,
                run_dir,
                settings=settings,
                quality_gates=quality_gates,
                repair_attempts=repair_attempts,
            )
            records.append(record)
            _write_json(
                output / "arm_summary.partial.json",
                {
                    **_arm_summary(records, arm=arm, replicates=replicates),
                    "last_observation": observation,
                },
            )
            if delay_seconds > 0 and observation.get("provider_invoked"):
                time.sleep(delay_seconds)

    summary = {
        **_arm_summary(records, arm=arm, replicates=replicates),
        "benchmark_digest": benchmark_digest(root),
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "settings": _settings_contract(settings),
        "settings_sha256": _settings_digest(settings),
        "cases": len(cases),
        "expected_records": len(cases) * replicates,
        "complete": len(records) == len(cases) * replicates,
    }
    _write_json(output / "arm_summary.json", summary)
    partial = output / "arm_summary.partial.json"
    if partial.exists():
        partial.unlink()
    return summary


def _metric_mean(records: list[GenerationRunRecord], name: str) -> float | None:
    values: list[float] = []
    for record in records:
        metric = record.metrics.get(name)
        if metric is None or not metric.measured:
            continue
        value = metric.value
        if isinstance(value, bool):
            values.append(float(int(value)))
        elif isinstance(value, (int, float)):
            values.append(float(value))
    return mean(values) if values else None


def _online_noise_floor(records: list[GenerationRunRecord]) -> dict[str, Any]:
    grouped: dict[str, list[GenerationRunRecord]] = defaultdict(list)
    for record in records:
        grouped[record.benchmark_case_id or record.task_id].append(record)

    cases: list[dict[str, Any]] = []
    for case_id, rows in sorted(grouped.items()):
        stage_distinct: dict[str, int] = {}
        for stage in _UPSTREAM_STAGES + _VARIANCE_STAGES:
            values = {
                item.stage_fingerprints[stage] for item in rows if stage in item.stage_fingerprints
            }
            stage_distinct[stage] = len(values)
        cases.append(
            {
                "case_id": case_id,
                "records": len(rows),
                "status_counts": dict(Counter(item.status for item in rows)),
                "stage_distinct_counts": stage_distinct,
                "sml_surface_variance": stage_distinct.get("sml", 0) > 1,
                "sir_variance": stage_distinct.get("sir", 0) > 1,
                "generated_tree_variance": stage_distinct.get("generated_tree", 0) > 1,
            }
        )

    return {
        "cases": cases,
        "canonical_context_stable_cases": sum(
            item["stage_distinct_counts"].get("canonical_semantic_context", 0) <= 1
            for item in cases
        ),
        "sml_surface_variance_cases": sum(bool(item["sml_surface_variance"]) for item in cases),
        "sir_variance_cases": sum(bool(item["sir_variance"]) for item in cases),
        "generated_tree_variance_cases": sum(
            bool(item["generated_tree_variance"]) for item in cases
        ),
    }


def _semantic_context_signature(record: GenerationRunRecord) -> str:
    return sha256_value(
        {
            stage: record.stage_fingerprints.get(stage)
            for stage in _UPSTREAM_STAGES
            if stage != "canonical_semantic_context"
        }
    )


def _normalized_strategy_record(record: GenerationRunRecord) -> GenerationRunRecord:
    payload = record.model_dump(mode="json")
    payload["record_id"] = "pending"
    stages = dict(payload["stage_fingerprints"])
    stages["canonical_semantic_context"] = _semantic_context_signature(record)
    payload["stage_fingerprints"] = stages
    draft = GenerationRunRecord.model_validate(payload)
    canonical = draft.model_dump(mode="json")
    canonical.pop("record_id", None)
    return draft.model_copy(update={"record_id": "sha256:" + sha256_value(canonical)})


def analyze_online_study(
    offline_dir: str | Path,
    online_dir: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    offline = load_records(offline_dir)
    online = load_records(online_dir)
    offline_normalized = [_normalized_strategy_record(item) for item in offline]
    online_normalized = [_normalized_strategy_record(item) for item in online]
    offline_map = {
        (item.benchmark_case_id or item.task_id, item.replicate_id): item
        for item in offline_normalized
    }
    online_map = {
        (item.benchmark_case_id or item.task_id, item.replicate_id): item
        for item in online_normalized
    }
    keys = sorted(set(offline_map) & set(online_map))

    upstream_mismatches: Counter[str] = Counter()
    exact_stage_matches: Counter[str] = Counter()
    stage_pair_counts: Counter[str] = Counter()
    status_matches = 0
    for key in keys:
        left, right = offline_map[key], online_map[key]
        status_matches += left.status == right.status
        for stage in _UPSTREAM_STAGES + _VARIANCE_STAGES:
            if stage not in left.stage_fingerprints or stage not in right.stage_fingerprints:
                continue
            stage_pair_counts[stage] += 1
            if left.stage_fingerprints[stage] == right.stage_fingerprints[stage]:
                exact_stage_matches[stage] += 1
            elif stage in _UPSTREAM_STAGES:
                upstream_mismatches[stage] += 1

    shared_metrics = [
        "compile_success",
        "generated_file_count",
        "oracle_requirement_recall",
        "oracle_foundation_recall",
        "oracle_capability_recall",
        "oracle_semantic_score",
    ]
    paired_assay = compare_releases(
        offline_normalized,
        online_normalized,
        metrics=shared_metrics,
        minimum_pairs=30,
        slice_keys=[
            "domain_pack",
            "database",
            "tenancy",
            "workflow",
            "rule_complexity",
            "source_style",
        ],
    )
    provider_invoked = sum(bool(item.metrics["provider_invoked"].value) for item in online)
    accepted = sum(item.status == "ACCEPTED" for item in online)
    final_conformance_measured = [
        item for item in online if item.metrics["final_candidate_conformance"].measured
    ]
    final_conformance_passes = sum(
        bool(item.metrics["final_candidate_conformance"].value)
        for item in final_conformance_measured
    )
    runtime_measured = [item for item in online if item.metrics["runtime_contract_pass"].measured]
    runtime_passes = sum(
        bool(item.metrics["runtime_contract_pass"].value) for item in runtime_measured
    )

    summary = {
        "kind": "Study1BOnlineAnalysis",
        "schema_version": STUDY_1B_SCHEMA_VERSION,
        "offline_records": len(offline),
        "online_records": len(online),
        "matched_pairs": len(keys),
        "status_match_rate": _rate(status_matches, len(keys)),
        "provider_invoked_records": provider_invoked,
        "online_acceptance_rate_when_invoked": _rate(accepted, provider_invoked),
        "final_conformance_pass_rate": _rate(
            final_conformance_passes, len(final_conformance_measured)
        ),
        "runtime_pass_rate": _rate(runtime_passes, len(runtime_measured)),
        "upstream_stage_mismatches": dict(upstream_mismatches),
        "upstream_stage_lock": not upstream_mismatches,
        "exact_stage_match_rates": {
            stage: _rate(exact_stage_matches[stage], stage_pair_counts[stage])
            for stage in _UPSTREAM_STAGES + _VARIANCE_STAGES
            if stage_pair_counts[stage]
        },
        "online_noise_floor": _online_noise_floor(online),
        "means": {
            name: {
                "offline": _metric_mean(offline, name),
                "online": _metric_mean(online, name),
            }
            for name in [
                *shared_metrics,
                "model_call_count",
                "repair_rounds",
                "model_latency_ms",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "runtime_contract_pass",
            ]
        },
        "paired_strategy_assay": paired_assay.model_dump(mode="json"),
    }
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "study1b_analysis.json", summary)
    return summary


def settings_from_cli(
    *,
    provider: str,
    model: str | None,
    temperature: float | None,
    timeout_seconds: int | None,
    max_retries: int | None,
    max_output_tokens: int | None,
) -> OnlineAgentSettings:
    return _settings_for_online(
        provider=provider,
        model=model,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        max_output_tokens=max_output_tokens,
    )
