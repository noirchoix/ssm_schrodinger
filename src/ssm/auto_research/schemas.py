from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ssm.auto_research.hashing import sha256_value

JsonScalar = str | int | float | bool | None


class EnvironmentIdentity(BaseModel):
    compiler_version: str
    python_version: str
    platform: str
    provider: str | None = None
    model: str | None = None
    scaffold_version: str | None = None
    prompt_version: str | None = None
    dependency_lock_sha256: str | None = None
    environment_lock_sha256: str
    attributes: dict[str, str] = Field(default_factory=dict)


class ArtifactReference(BaseModel):
    name: str
    kind: str
    relative_path: str
    sha256: str


class MetricObservation(BaseModel):
    name: str
    value: JsonScalar = None
    unit: str | None = None
    source: str | None = None
    measured: bool = True

    @model_validator(mode="after")
    def enforce_measured_only(self) -> MetricObservation:
        if not self.measured and self.value is not None:
            raise ValueError("An unmeasured metric must have a null value.")
        return self


class GenerationRunRecord(BaseModel):
    schema_version: str = "1.0"
    kind: str = "GenerationRunRecord"
    record_id: str
    run_id: str
    task_id: str
    benchmark_case_id: str | None = None
    replicate_id: str = "0"
    started_at: str
    completed_at: str
    status: Literal["ACCEPTED", "CONDITIONAL", "REJECTED", "ERROR"]
    reproducibility: Literal["REPRODUCIBLE", "NON_REPRODUCIBLE", "UNKNOWN"]
    source_name: str
    source_sha256: str
    environment: EnvironmentIdentity
    stage_fingerprints: dict[str, str] = Field(default_factory=dict)
    metrics: dict[str, MetricObservation] = Field(default_factory=dict)
    artifacts: list[ArtifactReference] = Field(default_factory=list)
    trace_ids: list[str] = Field(default_factory=list)
    eval_run_ids: list[str] = Field(default_factory=list)
    slices: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @classmethod
    def create(cls, **values: Any) -> GenerationRunRecord:
        payload = dict(values)
        payload["record_id"] = "pending"
        draft = cls.model_validate(payload)
        canonical = draft.model_dump(mode="json")
        canonical.pop("record_id", None)
        return draft.model_copy(update={"record_id": "sha256:" + sha256_value(canonical)})

    def verify_identity(self) -> bool:
        payload = self.model_dump(mode="json")
        identity = payload.pop("record_id", None)
        return isinstance(identity, str) and identity == "sha256:" + sha256_value(payload)


class TraceHeader(BaseModel):
    v: Literal[0] = 0
    t: Literal["trace"] = "trace"
    trace_id: str
    task: str
    started_at_ms: int
    sdk: str = "ssm-auto-research-python/1.0"
    attrs: dict[str, str] = Field(default_factory=dict)
    task_input: Any | None = None


class TraceSpan(BaseModel):
    v: Literal[0] = 0
    t: Literal["span"] = "span"
    trace_id: str
    span_id: int
    parent_span_id: int | None = None
    seq: int
    kind: Literal["model_call", "tool_call", "env_read", "memory_op", "branch", "span"]
    name: str
    input: Any = None
    output: Any = None
    error: str | None = None
    started_at_ms: int
    duration_ms: int
    attrs: dict[str, str] = Field(default_factory=dict)


class TraceTaskOutput(BaseModel):
    v: Literal[0] = 0
    t: Literal["task_output"] = "task_output"
    trace_id: str
    output: Any
    recorded_at_ms: int


class TraceDocument(BaseModel):
    header: TraceHeader
    spans: list[TraceSpan] = Field(default_factory=list)
    task_output: TraceTaskOutput | None = None
    partial: bool = False


class SignatureCensus(BaseModel):
    kind: str
    name: str
    input_sha256: str
    observations: int
    errors: int
    distinct_outputs: int
    classification: Literal["WITNESSED_DETERMINISTIC", "WITNESSED_DIVERGENT", "UNWITNESSED"]


class DeterminismCensusReport(BaseModel):
    schema_version: str = "1.0"
    kind: str = "DeterminismCensusReport"
    report_id: str
    task: str
    traces: int
    effectful_observations: int
    witnessed_observations: int
    deterministic_observations: int
    divergent_observations: int
    witnessed_coverage: float | None
    deterministic_fraction: float | None
    signatures: list[SignatureCensus] = Field(default_factory=list)

    @classmethod
    def create(cls, **values: Any) -> DeterminismCensusReport:
        payload = dict(values)
        payload["report_id"] = "pending"
        draft = cls.model_validate(payload)
        canonical = draft.model_dump(mode="json")
        canonical.pop("report_id", None)
        return draft.model_copy(update={"report_id": "sha256:" + sha256_value(canonical)})


class ReplayMismatch(BaseModel):
    index: int
    reason: str
    baseline_signature: str | None = None
    candidate_signature: str | None = None


class ReplayComparison(BaseModel):
    schema_version: str = "1.0"
    kind: str = "ReplayComparison"
    baseline_trace_id: str
    candidate_trace_id: str
    matched: int
    mismatches: list[ReplayMismatch] = Field(default_factory=list)
    equivalent: bool


class MetricRule(BaseModel):
    metric: str
    operator: Literal["eq", "ne", "lt", "le", "gt", "ge", "between", "present"]
    threshold: JsonScalar | list[JsonScalar] | None = None
    required: bool = True
    description: str = ""


class BehaviouralContract(BaseModel):
    schema_version: str = "1.0"
    kind: str = "BehaviouralContract"
    contract_id: str
    name: str
    rules: list[MetricRule]
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def create(
        cls, *, name: str, rules: list[MetricRule], metadata: dict[str, str] | None = None
    ) -> BehaviouralContract:
        payload = {
            "schema_version": "1.0",
            "kind": "BehaviouralContract",
            "name": name,
            "rules": [item.model_dump(mode="json") for item in rules],
            "metadata": metadata or {},
        }
        payload["contract_id"] = "sha256:" + sha256_value(payload)
        return cls.model_validate(payload)


class RuleVerification(BaseModel):
    metric: str
    verdict: Literal["PASS", "FAIL", "UNCHECKED"]
    observed: JsonScalar = None
    message: str


class EvaluationRun(BaseModel):
    schema_version: str = "1.0"
    kind: str = "EvaluationRun"
    eval_run_id: str
    contract_id: str
    generation_run_id: str
    verdict: Literal["PASS", "FAIL", "UNCHECKED"]
    outcomes: list[RuleVerification]
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(cls, **values: Any) -> EvaluationRun:
        payload = dict(values)
        payload["eval_run_id"] = "pending"
        draft = cls.model_validate(payload)
        canonical = draft.model_dump(mode="json")
        canonical.pop("eval_run_id", None)
        return draft.model_copy(update={"eval_run_id": "sha256:" + sha256_value(canonical)})


class TradeoffEnvelope(BaseModel):
    metric: str
    maximum_increase: float | None = None
    maximum_decrease: float | None = None
    maximum_absolute_change: float | None = None


class ChangeIntentContract(BaseModel):
    schema_version: str = "1.0"
    kind: str = "ChangeIntentContract"
    change_id: str
    baseline_release: str
    candidate_release: str
    objectives: list[str] = Field(default_factory=list)
    protected_metrics: list[str] = Field(default_factory=list)
    accepted_tradeoffs: list[TradeoffEnvelope] = Field(default_factory=list)
    affected_slices: dict[str, list[str]] = Field(default_factory=dict)
    approved: bool = False


class AssayMetricResult(BaseModel):
    metric: str
    pairs: int
    baseline_mean: float | None = None
    candidate_mean: float | None = None
    effect: float | None = None
    p_value: float | None = None
    significant: bool = False
    direction: Literal["increase", "decrease", "unchanged", "unknown"] = "unknown"
    method: str
    notes: list[str] = Field(default_factory=list)


class SliceAssayResult(BaseModel):
    slice_key: str
    slice_value: str
    verdict: Literal["NO_MATERIAL_CHANGE", "INTENDED_EVOLUTION", "REGRESSION", "INCONCLUSIVE"]
    metrics: list[AssayMetricResult] = Field(default_factory=list)


class StageAttribution(BaseModel):
    first_changed_stage: str | None = None
    changed_stage_counts: dict[str, int] = Field(default_factory=dict)
    examined_pairs: int = 0


class EvolutionAssayReport(BaseModel):
    schema_version: str = "1.0"
    kind: str = "EvolutionAssayReport"
    assay_id: str
    verdict: Literal["NO_MATERIAL_CHANGE", "INTENDED_EVOLUTION", "REGRESSION", "INCONCLUSIVE"]
    baseline_records: int
    candidate_records: int
    matched_pairs: int
    alpha: float
    metrics: list[AssayMetricResult] = Field(default_factory=list)
    slice_results: list[SliceAssayResult] = Field(default_factory=list)
    attribution: StageAttribution
    reasons: list[str] = Field(default_factory=list)
    change_intent_id: str | None = None

    @classmethod
    def create(cls, **values: Any) -> EvolutionAssayReport:
        payload = dict(values)
        payload["assay_id"] = "pending"
        draft = cls.model_validate(payload)
        canonical = draft.model_dump(mode="json")
        canonical.pop("assay_id", None)
        return draft.model_copy(update={"assay_id": "sha256:" + sha256_value(canonical)})


class BenchmarkCase(BaseModel):
    case_id: str
    intent_path: str
    title: str
    slices: dict[str, str]


class BenchmarkManifest(BaseModel):
    schema_version: str = "1.0"
    kind: str = "SSMBenchmarkManifest"
    benchmark_id: str
    name: str
    frozen: bool
    cases: list[BenchmarkCase]
    corpus_sha256: str
