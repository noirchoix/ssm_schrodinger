from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ssm.auto_research.assay import compare_releases
from ssm.auto_research.bench import validate_benchmark_manifest
from ssm.auto_research.contracts import verify_contract
from ssm.auto_research.records import load_generation_run_record
from ssm.auto_research.registry import ContentAddressedRegistry
from ssm.auto_research.schemas import (
    BehaviouralContract,
    ChangeIntentContract,
    EnvironmentIdentity,
    GenerationRunRecord,
    MetricObservation,
    MetricRule,
    TradeoffEnvelope,
)
from ssm.auto_research.trace import TraceRecorder, compare_traces, determinism_census
from ssm.product.compiler import SchrodingerProductCompiler

INTENT = """# Research Todo
Build an in-memory FastAPI Todo API with JWT and CRUD for title, completed, and due_date.
"""


def _environment() -> EnvironmentIdentity:
    return EnvironmentIdentity(
        compiler_version="2.6.0.dev2",
        python_version="3.13",
        platform="test",
        environment_lock_sha256="env",
    )


def _run(
    *,
    case: str,
    replicate: int,
    metric: float,
    stage: str = "same",
    slice_value: str = "generic_crud",
) -> GenerationRunRecord:
    return GenerationRunRecord.create(
        run_id=f"run:{case}:{replicate}",
        task_id=case,
        benchmark_case_id=case,
        replicate_id=str(replicate),
        started_at=datetime.now(UTC).isoformat(),
        completed_at=datetime.now(UTC).isoformat(),
        status="ACCEPTED",
        reproducibility="REPRODUCIBLE",
        source_name=f"{case}.md",
        source_sha256=f"source-{case}",
        environment=_environment(),
        stage_fingerprints={"requirements": "stable", "sml": stage},
        metrics={"quality": MetricObservation(name="quality", value=metric, source="test")},
        slices={"domain_pack": slice_value},
    )


def test_product_build_emits_canonical_run_record_and_trace(tmp_path: Path) -> None:
    output = tmp_path / "product"
    result = SchrodingerProductCompiler().build_text(
        INTENT,
        source_name="intent.md",
        out_dir=output,
        certification_repetitions=2,
        task_id="research-todo",
        benchmark_case_id="SSMB-TEST",
        replicate_id="3",
        slices={"domain_pack": "generic_crud"},
    )

    assert result.status in {"ACCEPTED", "CONDITIONAL"}
    record = load_generation_run_record(output / "generation_run.json")
    assert record.verify_identity()
    assert record.task_id == "research-todo"
    assert record.benchmark_case_id == "SSMB-TEST"
    assert record.replicate_id == "3"
    assert record.metrics["build_duration_ms"].measured is True
    assert record.stage_fingerprints["canonical_semantic_context"]
    assert record.stage_fingerprints["semantic_conformance"]
    assert record.stage_fingerprints["generated_tree"]
    assert record.trace_ids
    assert (output / "generation_trace.jsonl").exists()
    assert (output / "canonical_semantic_context.json").exists()
    assert (output / "semantic_conformance.json").exists()
    assert (output / "sir.json").exists()
    manifest = json.loads((output / "build_manifest.json").read_text(encoding="utf-8"))
    assert "generation_run.json" in manifest["files"]
    assert "generation_trace.jsonl" in manifest["files"]


def test_trace_determinism_and_replay_comparison(tmp_path: Path) -> None:
    first = TraceRecorder(tmp_path / "one.jsonl", task="draft")
    first.record("model_call", "mock:model", input_value={"prompt": "x"}, output={"text": "a"})
    first.set_task_output({"status": "ok"})
    second = TraceRecorder(tmp_path / "two.jsonl", task="draft")
    second.record("model_call", "mock:model", input_value={"prompt": "x"}, output={"text": "a"})
    second.set_task_output({"status": "ok"})
    third = TraceRecorder(tmp_path / "three.jsonl", task="draft")
    third.record("model_call", "mock:model", input_value={"prompt": "x"}, output={"text": "b"})
    third.set_task_output({"status": "ok"})

    stable = determinism_census([tmp_path / "one.jsonl", tmp_path / "two.jsonl"])
    assert stable.deterministic_fraction == 1.0
    assert stable.witnessed_coverage == 1.0
    divergent = determinism_census(
        [tmp_path / "one.jsonl", tmp_path / "two.jsonl", tmp_path / "three.jsonl"]
    )
    assert divergent.divergent_observations == 3
    same = compare_traces(tmp_path / "one.jsonl", tmp_path / "two.jsonl")
    changed = compare_traces(tmp_path / "one.jsonl", tmp_path / "three.jsonl")
    assert same.equivalent is True
    assert changed.equivalent is False
    assert changed.mismatches[0].reason == "recorded outcome differs"


def test_behavioural_contract_is_three_valued() -> None:
    run = _run(case="A", replicate=0, metric=0.9)
    passed_contract = BehaviouralContract.create(
        name="quality floor",
        rules=[MetricRule(metric="quality", operator="ge", threshold=0.8)],
    )
    passed = verify_contract(passed_contract, run)
    assert passed.verdict == "PASS"

    failed_contract = BehaviouralContract.create(
        name="strict quality floor",
        rules=[MetricRule(metric="quality", operator="ge", threshold=0.95)],
    )
    failed = verify_contract(failed_contract, run)
    assert failed.verdict == "FAIL"

    optional_contract = BehaviouralContract.create(
        name="optional cost",
        rules=[MetricRule(metric="cost_usd", operator="le", threshold=1.0, required=False)],
    )
    unchecked = verify_contract(optional_contract, run)
    assert unchecked.verdict == "UNCHECKED"


def test_stage_attribution_orders_canonical_context_before_sml() -> None:
    baseline: list[GenerationRunRecord] = []
    candidate: list[GenerationRunRecord] = []
    for index in range(6):
        left = _run(case="CTX", replicate=index, metric=10.0, stage="same")
        right = _run(case="CTX", replicate=index, metric=8.0, stage="same")
        left = left.model_copy(
            update={
                "stage_fingerprints": {
                    "requirements": "stable",
                    "canonical_semantic_context": "ctx-a",
                    "sml": "sml-a",
                }
            }
        )
        right = right.model_copy(
            update={
                "stage_fingerprints": {
                    "requirements": "stable",
                    "canonical_semantic_context": "ctx-b",
                    "sml": "sml-b",
                }
            }
        )
        baseline.append(left)
        candidate.append(right)

    report = compare_releases(baseline, candidate, metrics=["quality"], minimum_pairs=5)
    assert report.attribution.first_changed_stage == "canonical_semantic_context"


def test_content_addressed_registry_detects_tampering(tmp_path: Path) -> None:
    registry = ContentAddressedRegistry(tmp_path / "registry")
    payload = {"kind": "ExampleRecord", "value": 7}
    entry = registry.add(payload, signing_key="secret", key_id="test-key")
    assert registry.verify(entry.digest, signing_key="secret") is True
    object_path = tmp_path / "registry" / entry.stored_path
    object_path.write_text('{"kind":"ExampleRecord","value":8}', encoding="utf-8")
    try:
        registry.verify(entry.digest, signing_key="secret")
    except ValueError as exc:
        assert "digest mismatch" in str(exc)
    else:
        raise AssertionError("Tampered registry object was not rejected.")


def test_four_state_assay_and_stage_attribution() -> None:
    baseline = [_run(case="A", replicate=index, metric=10.0, stage="s1") for index in range(6)]
    unchanged = [_run(case="A", replicate=index, metric=10.0, stage="s1") for index in range(6)]
    no_change = compare_releases(baseline, unchanged, metrics=["quality"], minimum_pairs=5)
    assert no_change.verdict == "NO_MATERIAL_CHANGE"

    candidate = [_run(case="A", replicate=index, metric=8.0, stage="s2") for index in range(6)]
    regression = compare_releases(baseline, candidate, metrics=["quality"], minimum_pairs=5)
    assert regression.verdict == "REGRESSION"
    assert regression.attribution.first_changed_stage == "sml"
    assert any(item.verdict == "REGRESSION" for item in regression.slice_results)

    change = ChangeIntentContract(
        change_id="CHANGE-1",
        baseline_release="base",
        candidate_release="candidate",
        objectives=["reduce quality deliberately for lower cost"],
        accepted_tradeoffs=[TradeoffEnvelope(metric="quality", maximum_decrease=2.0)],
        approved=True,
    )
    intended = compare_releases(
        baseline,
        candidate,
        metrics=["quality"],
        minimum_pairs=5,
        change_intent=change,
    )
    assert intended.verdict == "INTENDED_EVOLUTION"

    inconclusive = compare_releases(
        baseline[:2], candidate[:2], metrics=["quality"], minimum_pairs=5
    )
    assert inconclusive.verdict == "INCONCLUSIVE"


def test_frozen_ssm_bench_v1_is_content_addressed() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = validate_benchmark_manifest(root / "benchmarks" / "ssm_bench_v1" / "manifest.json")
    assert manifest.frozen is True
    assert len(manifest.cases) == 30
    assert manifest.benchmark_id.startswith("sha256:")


def test_rbac_generation_is_hash_seed_independent() -> None:
    from ssm.backends.python_fastapi.platform import _rbac_py

    source = _rbac_py(
        [
            {"name": "Admin", "permissions": ["write", "read"]},
            {"name": "Viewer", "permissions": []},
        ]
    )
    assert "    'Admin': {'read', 'write'}," in source
    assert "    'Viewer': set()," in source
