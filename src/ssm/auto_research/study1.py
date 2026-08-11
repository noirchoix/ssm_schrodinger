from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Literal

from ssm.auto_research.assay import compare_releases
from ssm.auto_research.hashing import sha256_value
from ssm.auto_research.schemas import (
    ChangeIntentContract,
    EnvironmentIdentity,
    GenerationRunRecord,
    MetricObservation,
    TradeoffEnvelope,
)
from ssm.product.compiler import (
    IntentCompilationError,
    SchrodingerProductCompiler,
)

BENCHMARK_SCHEMA_VERSION = "2.0"
STUDY_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class LoadedCase:
    root: Path
    case_id: str
    title: str
    input_path: Path
    oracle_path: Path
    runtime_contract_path: Path
    metadata_path: Path
    oracle: dict[str, Any]
    runtime_contract: dict[str, Any]
    metadata: dict[str, Any]


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return {str(key): value for key, value in payload.items()}


def load_case(case_dir: str | Path) -> LoadedCase:
    root = Path(case_dir)
    metadata = _json(root / "metadata.json")
    return LoadedCase(
        root=root,
        case_id=str(metadata["case_id"]),
        title=str(metadata["title"]),
        input_path=root / "input.md",
        oracle_path=root / "oracle.json",
        runtime_contract_path=root / "runtime_contract.json",
        metadata_path=root / "metadata.json",
        oracle=_json(root / "oracle.json"),
        runtime_contract=_json(root / "runtime_contract.json"),
        metadata=metadata,
    )


def load_benchmark(root: str | Path) -> tuple[dict[str, Any], list[LoadedCase]]:
    benchmark_root = Path(root)
    manifest = _json(benchmark_root / "manifest.json")
    cases = [load_case(benchmark_root / item["case_path"]) for item in manifest["cases"]]
    return manifest, cases


def _canonical_text_bytes(path: Path) -> bytes:
    """Return platform-independent UTF-8 bytes for benchmark text hashing."""
    text = path.read_bytes().decode("utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.encode("utf-8")


def _case_file_hashes(case: LoadedCase) -> dict[str, str]:
    return {
        name: hashlib.sha256(_canonical_text_bytes(case.root / name)).hexdigest()
        for name in ["input.md", "oracle.json", "runtime_contract.json", "metadata.json"]
    }


def benchmark_digest(root: str | Path) -> str:
    manifest, cases = load_benchmark(root)
    payload = {
        "schema_version": manifest.get("schema_version"),
        "cases": [
            {
                "case_id": case.case_id,
                "files": _case_file_hashes(case),
            }
            for case in sorted(cases, key=lambda item: item.case_id)
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_benchmark(root: str | Path) -> dict[str, Any]:
    manifest, cases = load_benchmark(root)
    errors: list[str] = []
    if len(cases) != 30:
        errors.append(f"Expected 30 cases, found {len(cases)}")
    seen: set[str] = set()
    requirement_kinds: Counter[str] = Counter()
    source_styles: Counter[str] = Counter()
    expected_outcomes: Counter[str] = Counter()
    slices: dict[str, Counter[str]] = defaultdict(Counter)
    for case in cases:
        if case.case_id in seen:
            errors.append(f"Duplicate case id: {case.case_id}")
        seen.add(case.case_id)
        for required in [
            case.input_path,
            case.oracle_path,
            case.runtime_contract_path,
            case.metadata_path,
        ]:
            if not required.exists():
                errors.append(f"Missing {required}")
        for item in case.oracle.get("requirements", {}).get("must_include", []):
            requirement_kinds[str(item.get("kind"))] += 1
        source_styles[str(case.metadata.get("source_style", "unknown"))] += 1
        expected_outcomes[str(case.oracle.get("expected_outcome", "unknown"))] += 1
        for key, value in case.metadata.get("slices", {}).items():
            slices[str(key)][str(value)] += 1
    required_kinds = {
        "actor",
        "entity",
        "workflow",
        "business_rule",
        "integration",
        "security",
        "stack",
        "capability",
        "nonfunctional",
        "constraint",
        "report",
        "use_case",
    }
    missing_kinds = sorted(required_kinds - set(requirement_kinds))
    if missing_kinds:
        errors.append("Missing RequirementIR kind coverage: " + ", ".join(missing_kinds))
    computed = benchmark_digest(root)
    declared = str(manifest.get("corpus_digest", ""))
    if declared and declared != computed:
        errors.append(f"Corpus digest mismatch: declared={declared} computed={computed}")
    return {
        "kind": "SSMBenchV2Validation",
        "valid": not errors,
        "case_count": len(cases),
        "corpus_digest": computed,
        "requirement_kind_counts": dict(sorted(requirement_kinds.items())),
        "source_style_counts": dict(sorted(source_styles.items())),
        "expected_outcome_counts": dict(sorted(expected_outcomes.items())),
        "slice_counts": {k: dict(sorted(v.items())) for k, v in sorted(slices.items())},
        "errors": errors,
    }


def _norm(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _requirement_score(context: Any, oracle: dict[str, Any]) -> tuple[float, list[str]]:
    expected = oracle.get("requirements", {}).get("must_include", [])
    if not expected:
        return 1.0, []
    actual = {(_norm(item.kind), _norm(item.name)) for item in context.requirements.requirements}
    missing: list[str] = []
    for item in expected:
        key = (_norm(str(item["kind"])), _norm(str(item["name"])))
        if key not in actual:
            missing.append(f"{item['kind']}:{item['name']}")
    return (len(expected) - len(missing)) / len(expected), missing


def _foundation_score(context: Any, oracle: dict[str, Any]) -> tuple[float, list[str]]:
    foundation = oracle.get("foundation", {})
    obligations: list[tuple[str, bool]] = []
    actual_entities = {_norm(item.name) for item in context.foundation.entities}
    for entity in foundation.get("entities", []):
        obligations.append((f"entity:{entity}", _norm(entity) in actual_entities))
    actual_workflows = {_norm(item.name) for item in context.foundation.workflows}
    for workflow in foundation.get("workflows", []):
        obligations.append((f"workflow:{workflow}", _norm(workflow) in actual_workflows))
    actual_rules = {_norm(item.name) for item in context.foundation.business_rules}
    for rule in foundation.get("business_rules", []):
        obligations.append((f"business_rule:{rule}", _norm(rule) in actual_rules))
    actual_reports = {_norm(item) for item in context.foundation.reports}
    for report in foundation.get("reports", []):
        obligations.append((f"report:{report}", _norm(report) in actual_reports))
    for key in ["database", "auth", "tenant_enabled", "audit_enabled"]:
        if key in foundation:
            obligations.append((key, getattr(context.foundation, key) == foundation[key]))
    if not obligations:
        return 1.0, []
    missing = [name for name, ok in obligations if not ok]
    return (len(obligations) - len(missing)) / len(obligations), missing


def _capability_score(context: Any, oracle: dict[str, Any]) -> tuple[float, list[str]]:
    expected = oracle.get("capabilities", {}).get("required_ids", [])
    actual = {item.capability_id for item in context.capabilities.selected}
    missing = [item for item in expected if item not in actual]
    if not expected:
        return 1.0, []
    return (len(expected) - len(missing)) / len(expected), missing


def evaluate_oracle(context: Any, oracle: dict[str, Any]) -> dict[str, Any]:
    req_score, req_missing = _requirement_score(context, oracle)
    foundation_score, foundation_missing = _foundation_score(context, oracle)
    capability_score, capability_missing = _capability_score(context, oracle)
    expected_ambiguities = {
        _norm(item) for item in oracle.get("requirements", {}).get("ambiguity_topics", [])
    }
    actual_ambiguities = {_norm(item.topic) for item in context.requirements.ambiguities}
    ambiguity_score = 1.0 if expected_ambiguities.issubset(actual_ambiguities) else 0.0
    expected_contradictions = {
        _norm(item) for item in oracle.get("requirements", {}).get("contradiction_topics", [])
    }
    actual_contradictions = {_norm(item.topic) for item in context.requirements.contradictions}
    contradiction_score = 1.0 if expected_contradictions.issubset(actual_contradictions) else 0.0
    expected_unsupported = {
        _norm(item) for item in oracle.get("requirements", {}).get("unsupported_features", [])
    }
    actual_unsupported = {_norm(item) for item in context.requirements.unsupported_features}
    unsupported_score = 1.0 if expected_unsupported.issubset(actual_unsupported) else 0.0
    scores = [
        req_score,
        foundation_score,
        capability_score,
        ambiguity_score,
        contradiction_score,
        unsupported_score,
    ]
    return {
        "requirement_obligation_recall": req_score,
        "foundation_obligation_recall": foundation_score,
        "capability_obligation_recall": capability_score,
        "ambiguity_detection": ambiguity_score,
        "contradiction_detection": contradiction_score,
        "unsupported_detection": unsupported_score,
        "semantic_oracle_score": mean(scores),
        "missing": {
            "requirements": req_missing,
            "foundation": foundation_missing,
            "capabilities": capability_missing,
        },
    }


def _runtime_probe_script() -> str:
    return r"""
import json, os, sys, tempfile
from pathlib import Path
contract=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
os.environ.setdefault("JWT_SECRET_KEY", "study1-test-secret-key-change-me-32-bytes")
os.environ.setdefault("CREATE_DB_ON_STARTUP", "true")
if contract.get("database") == "PostgreSQL":
    db=Path(tempfile.mkdtemp(prefix="ssmb2-runtime-"))/"runtime.db"
    os.environ["DATABASE_URL"]="sqlite:///"+db.as_posix()
from fastapi.testclient import TestClient
from app.main import app
try:
    from app.core.security import create_access_token
except Exception:
    create_access_token=None
results=[]
openapi=app.openapi()
paths=openapi.get("paths", {})
headers={}
if create_access_token is not None:
    token=create_access_token(subject="study1", scopes=["read","write","admin"], roles=["Admin","manager","hr_admin","approver","agent","registrar"])
    headers={"Authorization":f"Bearer {token}","x-tenant-id":"00000000-0000-4000-8000-000000000001"}
with TestClient(app) as client:
    for check in contract.get("checks", []):
        kind=check["kind"]
        ok=False; observed=None
        if kind=="readyz":
            r=client.get("/readyz"); observed=r.status_code; ok=r.status_code==check.get("status",200)
        elif kind=="route_exists":
            path=check["path"]; method=check["method"].lower(); observed=method in paths.get(path,{}); ok=bool(observed)
        elif kind=="unauthenticated_status":
            r=client.request(check["method"],check["path"]); observed=r.status_code; ok=r.status_code in check.get("statuses",[401,403])
        elif kind=="authenticated_status":
            r=client.request(check["method"],check["path"],headers=headers); observed=r.status_code; ok=r.status_code in check.get("statuses",[200])
        results.append({"kind":kind,"ok":ok,"observed":observed,"check":check})
print(json.dumps({"passed":all(x["ok"] for x in results),"checks":results},sort_keys=True))
"""


def execute_runtime_contract(generated_app: Path, contract_path: Path) -> dict[str, Any]:
    contract = _json(contract_path)
    if contract.get("mode") == "skip":
        return {
            "passed": True,
            "skipped": True,
            "reason": contract.get("reason", "expected rejection"),
        }
    with tempfile.TemporaryDirectory(prefix="ssmb2-probe-") as tmp:
        script = Path(tmp) / "probe.py"
        script.write_text(_runtime_probe_script(), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(generated_app.resolve())
        completed = subprocess.run(
            [sys.executable, str(script), str(contract_path.resolve())],
            cwd=generated_app,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    if completed.returncode != 0:
        return {
            "passed": False,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-4000:],
        }
    lines = [line for line in completed.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        return {
            "passed": False,
            "returncode": 0,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    payload = json.loads(lines[-1])
    if not isinstance(payload, dict):
        return {
            "passed": False,
            "returncode": 0,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "reason": "runtime probe did not return a JSON object",
        }
    return {str(key): value for key, value in payload.items()}


def qualify_benchmark(root: str | Path, out_dir: str | Path) -> dict[str, Any]:
    validation = validate_benchmark(root)
    if not validation["valid"]:
        raise ValueError("Benchmark manifest validation failed: " + "; ".join(validation["errors"]))
    _, cases = load_benchmark(root)
    output = Path(out_dir)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    compiler = SchrodingerProductCompiler()
    results: list[dict[str, Any]] = []
    harness_errors = 0
    for case in cases:
        case_out = output / case.case_id
        case_out.mkdir(parents=True)
        text = case.input_path.read_text(encoding="utf-8")
        started = time.monotonic()
        result: dict[str, Any] = {"case_id": case.case_id, "title": case.title}
        try:
            context = compiler.prepare_semantic_context(text, source_name=str(case.input_path))
            oracle_eval = evaluate_oracle(context, case.oracle)
            blocking = compiler.semantic_context_blocking_reasons(context)
            expected = case.oracle["expected_outcome"]
            result.update(
                {"oracle": oracle_eval, "blocking": blocking, "expected_outcome": expected}
            )
            build = None
            system_error = None
            if blocking:
                actual_outcome = "REJECTED"
            else:
                try:
                    build = compiler.build_text(
                        text,
                        source_name=str(case.input_path),
                        out_dir=case_out,
                        certification_repetitions=1,
                        task_id=f"study1-qualification-{case.case_id}",
                        benchmark_case_id=case.case_id,
                        replicate_id="Q0",
                        slices=case.metadata.get("slices", {}),
                    )
                    actual_outcome = "GENERATABLE"
                except IntentCompilationError as exc:
                    actual_outcome = "REJECTED"
                    system_error = f"{type(exc).__name__}: {exc}"
            result["actual_outcome"] = actual_outcome
            if system_error:
                result["system_error"] = system_error
            if build is not None:
                result["build_status"] = build.status
                result["generated_file_count"] = build.generated_file_count
                result["runtime"] = execute_runtime_contract(
                    case_out / "generated_app", case.runtime_contract_path
                )
            else:
                result["runtime"] = {
                    "passed": case.runtime_contract.get("mode") == "skip",
                    "skipped": True,
                    "reason": "No generated application: fail-closed or conformance rejection.",
                }
            expected_ok = (expected == "REJECTED" and actual_outcome == "REJECTED") or (
                expected != "REJECTED" and actual_outcome == "GENERATABLE"
            )
            result["expected_outcome_match"] = expected_ok
            result["harness_ok"] = True
        except Exception as exc:  # evaluator/instrumentation failure, not product failure
            harness_errors += 1
            result.update({"harness_ok": False, "error": f"{type(exc).__name__}: {exc}"})
        result["duration_ms"] = int((time.monotonic() - started) * 1000)
        (case_out / "qualification_result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        results.append(result)
    measured = [item for item in results if item.get("harness_ok")]
    summary = {
        "kind": "SSMBenchV2Qualification",
        "schema_version": STUDY_SCHEMA_VERSION,
        "case_count": len(results),
        "harness_errors": harness_errors,
        "harness_qualified": harness_errors == 0,
        "expected_outcome_matches": sum(
            bool(item.get("expected_outcome_match")) for item in results
        ),
        "runtime_passes": sum(bool(item.get("runtime", {}).get("passed")) for item in results),
        "runtime_executed": sum(
            not bool(item.get("runtime", {}).get("skipped")) for item in results
        ),
        "mean_semantic_oracle_score": mean(
            item.get("oracle", {}).get("semantic_oracle_score", 0.0) for item in measured
        )
        if measured
        else 0.0,
        "cases": results,
    }
    (output / "qualification_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def _environment_identity() -> EnvironmentIdentity:
    lock = sha256_value(
        {"python": sys.version, "platform": sys.platform, "study": STUDY_SCHEMA_VERSION}
    )
    return EnvironmentIdentity(
        compiler_version="2.6.0.dev2",
        python_version=sys.version.split()[0],
        platform=sys.platform,
        environment_lock_sha256=lock,
        scaffold_version="ssm-bench-v2-study1",
        prompt_version="canonical-offline-v1",
    )


def observe_case(case: LoadedCase, replicate_id: str) -> GenerationRunRecord:
    compiler = SchrodingerProductCompiler()
    text = case.input_path.read_text(encoding="utf-8")
    started = datetime.now(UTC)
    context = compiler.prepare_semantic_context(text, source_name=str(case.input_path))
    oracle_eval = evaluate_oracle(context, case.oracle)
    blocking = compiler.semantic_context_blocking_reasons(context)
    errors = list(blocking)
    status: Literal["ACCEPTED", "CONDITIONAL", "REJECTED", "ERROR"] = (
        "REJECTED" if blocking else "ACCEPTED"
    )
    stage_fingerprints = {
        "requirements": context.requirements.semantic_fingerprint,
        "foundation": sha256_value(context.foundation.model_dump(mode="json")),
        "architecture": context.architecture.semantic_fingerprint,
        "capabilities": context.capabilities.semantic_fingerprint,
        "negotiation": sha256_value(context.negotiation.model_dump(mode="json")),
        "canonical_semantic_context": context.semantic_fingerprint,
    }
    generated_count = 0
    semantic_variance = 0.0
    requirements_coverage = oracle_eval["requirement_obligation_recall"]
    capability_honesty = oracle_eval["capability_obligation_recall"]
    if not blocking:
        sml_text = compiler.renderer.render(
            context.foundation,
            architecture_pattern=context.architecture.selected_pattern,
        )
        conformance = compiler.conformance_verifier.verify(
            context,
            sml_text,
            source_file=f"{case.input_path}::project.sml.md",
        )
        stage_fingerprints["sml"] = sha256_value(sml_text)
        stage_fingerprints["semantic_conformance"] = conformance.semantic_fingerprint
        if not conformance.accepted:
            status = "REJECTED"
            errors.append(compiler.conformance_verifier.format_diagnostics(conformance))
        else:
            compiled = compiler.compiler.compile_text(
                sml_text,
                source_file=f"{case.input_path}::project.sml.md",
            )
            certification = compiler.certifier.certify(
                source_text=text,
                source_name=str(case.input_path),
                requirements=context.requirements,
                foundation=context.foundation,
                architecture=context.architecture,
                capabilities=context.capabilities,
                negotiation=context.negotiation,
                sml_text=sml_text,
                compile_result=compiled,
                repetitions=1,
            )
            sir = compiled.sir
            stage_fingerprints.update(
                {
                    "sir": sha256_value(sir.model_dump(mode="json") if sir is not None else {}),
                    "generated_tree": sha256_value(
                        {item.path: sha256_value(item.content) for item in compiled.files}
                    ),
                    "quality_gates": sha256_value(certification.model_dump(mode="json")),
                }
            )
            generated_count = len(compiled.files)
            semantic_variance = certification.variability.semantic_variance_score
            requirements_coverage = certification.metrics.requirements_coverage
            capability_honesty = certification.metrics.capability_honesty
            status = (
                "REJECTED"
                if certification.status == "REJECTED"
                else "CONDITIONAL"
                if certification.status == "CONDITIONAL_SUPPORTED_PROFILE"
                else "ACCEPTED"
            )
    metrics = {
        "compile_success": MetricObservation(
            name="compile_success", value=status != "REJECTED", source="study1_observation"
        ),
        "generated_file_count": MetricObservation(
            name="generated_file_count",
            value=generated_count,
            unit="files",
            source="study1_observation",
        ),
        "semantic_variance_score": MetricObservation(
            name="semantic_variance_score", value=semantic_variance, source="certification"
        ),
        "requirements_coverage": MetricObservation(
            name="requirements_coverage", value=requirements_coverage, source="certification"
        ),
        "capability_honesty": MetricObservation(
            name="capability_honesty", value=capability_honesty, source="certification"
        ),
        "oracle_requirement_recall": MetricObservation(
            name="oracle_requirement_recall",
            value=oracle_eval["requirement_obligation_recall"],
            source="independent_oracle",
        ),
        "oracle_foundation_recall": MetricObservation(
            name="oracle_foundation_recall",
            value=oracle_eval["foundation_obligation_recall"],
            source="independent_oracle",
        ),
        "oracle_capability_recall": MetricObservation(
            name="oracle_capability_recall",
            value=oracle_eval["capability_obligation_recall"],
            source="independent_oracle",
        ),
        "oracle_semantic_score": MetricObservation(
            name="oracle_semantic_score",
            value=oracle_eval["semantic_oracle_score"],
            source="independent_oracle",
        ),
    }
    return GenerationRunRecord.create(
        run_id=f"study1-{case.case_id}-{replicate_id}",
        task_id=case.case_id,
        benchmark_case_id=case.case_id,
        replicate_id=replicate_id,
        started_at=started.isoformat(),
        completed_at=datetime.now(UTC).isoformat(),
        status=status,
        reproducibility="UNKNOWN",
        source_name=str(case.input_path),
        source_sha256=sha256_value(text),
        environment=_environment_identity(),
        stage_fingerprints=stage_fingerprints,
        metrics=metrics,
        artifacts=[],
        trace_ids=[],
        eval_run_ids=[],
        slices={str(k): str(v) for k, v in case.metadata.get("slices", {}).items()},
        warnings=[],
        errors=errors,
    )


def run_repeated_arm(
    root: str | Path,
    out_dir: str | Path,
    *,
    arm: str,
    replicates: int = 10,
) -> dict[str, Any]:
    _, cases = load_benchmark(root)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    records: list[GenerationRunRecord] = []
    for case in cases:
        for index in range(replicates):
            replicate_id = f"R{index:02d}"
            record = observe_case(case, replicate_id)
            case_dir = output / case.case_id / replicate_id
            case_dir.mkdir(parents=True, exist_ok=True)
            (case_dir / "generation_run.json").write_text(
                record.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
            records.append(record)
    summary = {
        "kind": "Study1RepeatedArm",
        "arm": arm,
        "cases": len(cases),
        "replicates": replicates,
        "records": len(records),
        "status_counts": dict(Counter(record.status for record in records)),
        "mean_oracle_semantic_score": mean(
            float(record.metrics["oracle_semantic_score"].value or 0.0) for record in records
        ),
    }
    (output / "arm_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def load_records(root: str | Path) -> list[GenerationRunRecord]:
    result = []
    for path in sorted(Path(root).rglob("generation_run.json")):
        result.append(GenerationRunRecord.model_validate_json(path.read_text(encoding="utf-8")))
    return result


def _mutated_record(record: GenerationRunRecord, mutation: str) -> GenerationRunRecord:
    payload = record.model_dump(mode="json")
    payload["record_id"] = "pending"
    stages = dict(payload["stage_fingerprints"])
    metrics = dict(payload["metrics"])
    marker = sha256_value(
        {
            "mutation": mutation,
            "case": record.benchmark_case_id,
            "replicate": record.replicate_id,
        }
    )

    if mutation == "requirements_drop":
        if record.slices.get("security") in {"jwt", "mixed"}:
            stages["requirements"] = marker
            downstream_stages = [
                "foundation",
                "architecture",
                "capabilities",
                "negotiation",
                "canonical_semantic_context",
                "sml",
                "semantic_conformance",
                "sir",
                "generated_tree",
                "quality_gates",
            ]
            for stage in downstream_stages:
                if stage in stages:
                    stages[stage] = sha256_value({"upstream": marker, "stage": stage})
            metrics["oracle_requirement_recall"]["value"] = max(
                0.0,
                float(metrics["oracle_requirement_recall"]["value"]) - 0.25,
            )
            metrics["oracle_semantic_score"]["value"] = max(
                0.0,
                float(metrics["oracle_semantic_score"]["value"]) - 0.10,
            )
    elif mutation == "sml_rule_drop":
        if record.slices.get("rule_complexity") not in {"none", None}:
            stages["sml"] = marker
            for stage in [
                "semantic_conformance",
                "sir",
                "generated_tree",
                "quality_gates",
            ]:
                if stage in stages:
                    stages[stage] = sha256_value({"upstream": marker, "stage": stage})
            metrics["compile_success"]["value"] = False
            metrics["oracle_semantic_score"]["value"] = max(
                0.0,
                float(metrics["oracle_semantic_score"]["value"]) - 0.15,
            )
    elif mutation == "generated_tree_drop":
        if "generated_tree" in stages:
            stages["generated_tree"] = marker
            stages["quality_gates"] = sha256_value({"upstream": marker, "stage": "quality_gates"})
            metrics["compile_success"]["value"] = False
    elif mutation == "intended_evolution" and "generated_tree" in stages:
        stages["generated_tree"] = marker
        metrics["generated_file_count"]["value"] = (
            int(metrics["generated_file_count"]["value"] or 0) + 1
        )

    payload["stage_fingerprints"] = stages
    payload["metrics"] = metrics
    draft = GenerationRunRecord.model_validate(payload)
    canonical = draft.model_dump(mode="json")
    canonical.pop("record_id", None)
    return draft.model_copy(update={"record_id": "sha256:" + sha256_value(canonical)})


def write_mutation_arm(
    baseline_dir: str | Path, out_dir: str | Path, mutation: str
) -> dict[str, Any]:
    baseline = load_records(baseline_dir)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    records: list[GenerationRunRecord] = []
    for record in baseline:
        mutated = _mutated_record(record, mutation)
        record_dir = output / (record.benchmark_case_id or record.task_id) / record.replicate_id
        record_dir.mkdir(parents=True, exist_ok=True)
        (record_dir / "generation_run.json").write_text(
            mutated.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        records.append(mutated)
    return {"mutation": mutation, "records": len(records)}


def analyze_study(
    baseline_dir: str | Path,
    control_dir: str | Path,
    perturbation_root: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    baseline = load_records(baseline_dir)
    control = load_records(control_dir)
    metrics = [
        "compile_success",
        "generated_file_count",
        "oracle_requirement_recall",
        "oracle_semantic_score",
    ]
    slice_keys = [
        "domain_pack",
        "database",
        "tenancy",
        "workflow",
        "rule_complexity",
        "source_style",
    ]
    no_change = compare_releases(
        baseline,
        control,
        metrics=metrics,
        minimum_pairs=30,
        slice_keys=slice_keys,
    )
    reports = {"no_change": no_change.model_dump(mode="json")}

    for name in ["requirements_drop", "sml_rule_drop", "generated_tree_drop"]:
        candidate = load_records(Path(perturbation_root) / name)
        report = compare_releases(
            baseline,
            candidate,
            metrics=metrics,
            minimum_pairs=30,
            slice_keys=slice_keys,
        )
        reports[name] = report.model_dump(mode="json")

    intended = load_records(Path(perturbation_root) / "intended_evolution")
    change = ChangeIntentContract(
        change_id="study1-intended-extra-evidence-file",
        baseline_release="v2.6.0-dev2-study1-baseline",
        candidate_release="v2.6.0-dev2-study1-intended",
        objectives=["Add one non-semantic evidence artifact per generated application."],
        protected_metrics=[
            "compile_success",
            "oracle_requirement_recall",
            "oracle_semantic_score",
        ],
        accepted_tradeoffs=[TradeoffEnvelope(metric="generated_file_count", maximum_increase=1.0)],
        approved=True,
    )
    intended_report = compare_releases(
        baseline,
        intended,
        metrics=metrics,
        minimum_pairs=30,
        change_intent=change,
        slice_keys=slice_keys,
    )
    reports["intended_evolution"] = intended_report.model_dump(mode="json")

    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary = {
        "kind": "Study1Analysis",
        "baseline_records": len(baseline),
        "control_records": len(control),
        "verdicts": {name: payload["verdict"] for name, payload in reports.items()},
        "first_changed_stage": {
            name: payload["attribution"]["first_changed_stage"] for name, payload in reports.items()
        },
        "reports": reports,
    }
    (output / "study1_analysis.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
