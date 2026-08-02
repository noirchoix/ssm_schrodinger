"""Auto-inspired reproducibility and evolution-assurance control plane for SSM."""

from ssm.auto_research.assay import compare_releases, load_run_records
from ssm.auto_research.bench import validate_benchmark_manifest
from ssm.auto_research.contracts import verify_contract
from ssm.auto_research.records import load_generation_run_record
from ssm.auto_research.registry import ContentAddressedRegistry
from ssm.auto_research.schemas import (
    BehaviouralContract,
    ChangeIntentContract,
    DeterminismCensusReport,
    EvaluationRun,
    EvolutionAssayReport,
    GenerationRunRecord,
    MetricObservation,
    MetricRule,
    ReplayComparison,
)
from ssm.auto_research.trace import compare_traces, determinism_census, load_trace

__all__ = [
    "BehaviouralContract",
    "ChangeIntentContract",
    "ContentAddressedRegistry",
    "DeterminismCensusReport",
    "EvaluationRun",
    "EvolutionAssayReport",
    "GenerationRunRecord",
    "MetricObservation",
    "MetricRule",
    "ReplayComparison",
    "compare_releases",
    "compare_traces",
    "determinism_census",
    "load_generation_run_record",
    "load_run_records",
    "load_trace",
    "validate_benchmark_manifest",
    "verify_contract",
]
