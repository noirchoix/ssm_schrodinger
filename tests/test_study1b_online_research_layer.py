from __future__ import annotations

import json
from pathlib import Path

from ssm.agents.settings import OnlineAgentSettings
from ssm.auto_research.study1 import load_case
from ssm.auto_research.study1b import (
    _trace_observations,
    observe_online_case,
    require_live_opt_in,
)

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "ssm_bench_v2" / "cases"


def _mock_settings() -> OnlineAgentSettings:
    return OnlineAgentSettings(
        run_online_ai=True,
        agent_mode="online",
        llm_provider="mock",
        llm_model="mock",
        llm_max_retries=1,
    )


def test_trace_observations_aggregate_usage(tmp_path: Path) -> None:
    trace = tmp_path / "generation_trace.jsonl"
    rows = [
        {"t": "trace", "trace_id": "trace-1"},
        {
            "t": "span",
            "kind": "model_call",
            "duration_ms": 12,
            "error": None,
            "output": {
                "response_sha256": "a",
                "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            },
        },
        {
            "t": "span",
            "kind": "model_call",
            "duration_ms": 8,
            "error": None,
            "output": {
                "response_sha256": "b",
                "usage": {"input_tokens": 11, "output_tokens": 5, "total_tokens": 16},
            },
        },
    ]
    trace.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    observed = _trace_observations(trace)
    assert observed["trace_id"] == "trace-1"
    assert observed["provider_invoked"] is True
    assert observed["model_call_count"] == 2
    assert observed["model_latency_ms"] == 20
    assert observed["input_tokens"] == 21
    assert observed["output_tokens"] == 9
    assert observed["total_tokens"] == 30


def test_mock_online_case_records_stochastic_boundary(tmp_path: Path) -> None:
    case = load_case(BENCH / "SSMB2-015")
    record, observation = observe_online_case(
        case,
        "R00",
        tmp_path / "SSMB2-015" / "R00",
        settings=_mock_settings(),
        quality_gates=False,
        repair_attempts=2,
    )
    assert record.verify_identity()
    assert record.benchmark_case_id == "SSMB2-015"
    assert record.environment.provider == "mock"
    assert record.environment.attributes["generation_strategy"] == "online"
    assert record.metrics["provider_invoked"].value is True
    assert record.metrics["canonical_context_lock"].value is True
    assert observation["canonical_context_lock"] is True
    assert "canonical_semantic_context" in record.stage_fingerprints
    assert "sml" in record.stage_fingerprints


def test_blocked_case_never_invokes_provider(tmp_path: Path) -> None:
    case = load_case(BENCH / "SSMB2-027")
    record, observation = observe_online_case(
        case,
        "R00",
        tmp_path / "SSMB2-027" / "R00",
        settings=_mock_settings(),
        quality_gates=False,
        repair_attempts=2,
    )
    assert record.verify_identity()
    assert record.status == "REJECTED"
    assert record.metrics["provider_invoked"].value is False
    assert observation["provider_invoked"] is False
    assert observation["blocking"]


def test_mock_provider_does_not_require_live_opt_in() -> None:
    require_live_opt_in("mock")
