from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from statistics import mean
from typing import Literal

from ssm.auto_research.schemas import (
    AssayMetricResult,
    ChangeIntentContract,
    EvolutionAssayReport,
    GenerationRunRecord,
    SliceAssayResult,
    StageAttribution,
)


class AssayError(ValueError):
    pass


def load_run_records(path: str | Path) -> list[GenerationRunRecord]:
    root = Path(path)
    files = [root] if root.is_file() else sorted(root.rglob("generation_run.json"))
    records: list[GenerationRunRecord] = []
    for file in files:
        payload = json.loads(file.read_text(encoding="utf-8"))
        record = GenerationRunRecord.model_validate(payload)
        if not record.verify_identity():
            raise AssayError(f"Generation run identity mismatch: {file}")
        records.append(record)
    return records


def compare_releases(
    baseline: list[GenerationRunRecord],
    candidate: list[GenerationRunRecord],
    *,
    metrics: list[str] | None = None,
    alpha: float = 0.05,
    minimum_pairs: int = 5,
    change_intent: ChangeIntentContract | None = None,
    slice_keys: list[str] | None = None,
) -> EvolutionAssayReport:
    baseline_map = {_pair_key(item): item for item in baseline}
    candidate_map = {_pair_key(item): item for item in candidate}
    keys = sorted(set(baseline_map) & set(candidate_map))
    pairs = [(baseline_map[key], candidate_map[key]) for key in keys]
    selected_metrics = metrics or _discover_metrics(pairs)
    metric_results = [_assay_metric(name, pairs, alpha) for name in selected_metrics]
    attribution = _stage_attribution(pairs)
    slice_results = _slice_results(
        pairs,
        selected_metrics,
        alpha=alpha,
        minimum_pairs=minimum_pairs,
        change_intent=change_intent,
        slice_keys=slice_keys
        or ["domain_pack", "database", "tenancy", "workflow", "update_model", "rule_complexity"],
    )
    reasons: list[str] = []
    verdict = _overall_verdict(
        metric_results,
        matched_pairs=len(pairs),
        minimum_pairs=minimum_pairs,
        change_intent=change_intent,
        reasons=reasons,
    )
    if any(item.verdict == "REGRESSION" for item in slice_results):
        verdict = "REGRESSION"
        reasons.append("At least one labelled capability slice contains a material regression.")
    return EvolutionAssayReport.create(
        verdict=verdict,
        baseline_records=len(baseline),
        candidate_records=len(candidate),
        matched_pairs=len(pairs),
        alpha=alpha,
        metrics=metric_results,
        slice_results=slice_results,
        attribution=attribution,
        reasons=reasons,
        change_intent_id=change_intent.change_id if change_intent else None,
    )


def _pair_key(record: GenerationRunRecord) -> tuple[str, str]:
    return (record.benchmark_case_id or record.task_id, record.replicate_id)


def _discover_metrics(pairs: list[tuple[GenerationRunRecord, GenerationRunRecord]]) -> list[str]:
    if not pairs:
        return []
    common = set(pairs[0][0].metrics) & set(pairs[0][1].metrics)
    for left, right in pairs[1:]:
        common &= set(left.metrics) & set(right.metrics)
    numeric = []
    for name in sorted(common):
        values = [pair[0].metrics[name].value for pair in pairs] + [
            pair[1].metrics[name].value for pair in pairs
        ]
        if all(isinstance(value, (int, float, bool)) for value in values if value is not None):
            numeric.append(name)
    return numeric


def _numeric_pairs(
    metric: str, pairs: Iterable[tuple[GenerationRunRecord, GenerationRunRecord]]
) -> list[tuple[float, float]]:
    values: list[tuple[float, float]] = []
    for left, right in pairs:
        left_obs = left.metrics.get(metric)
        right_obs = right.metrics.get(metric)
        if left_obs is None or right_obs is None:
            continue
        if not left_obs.measured or not right_obs.measured:
            continue
        left_value, right_value = left_obs.value, right_obs.value
        if isinstance(left_value, bool):
            left_value = int(left_value)
        if isinstance(right_value, bool):
            right_value = int(right_value)
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            values.append((float(left_value), float(right_value)))
    return values


def _assay_metric(
    metric: str,
    pairs: list[tuple[GenerationRunRecord, GenerationRunRecord]],
    alpha: float,
) -> AssayMetricResult:
    values = _numeric_pairs(metric, pairs)
    if not values:
        return AssayMetricResult(
            metric=metric,
            pairs=0,
            method="paired-sign-test",
            notes=["No paired measured numeric observations."],
        )
    differences = [right - left for left, right in values]
    nonzero = [item for item in differences if item != 0]
    positive = sum(item > 0 for item in nonzero)
    negative = sum(item < 0 for item in nonzero)
    p_value = _two_sided_binomial(min(positive, negative), len(nonzero)) if nonzero else 1.0
    effect = mean(differences)
    direction: Literal["increase", "decrease", "unchanged", "unknown"] = (
        "increase" if effect > 0 else "decrease" if effect < 0 else "unchanged"
    )
    return AssayMetricResult(
        metric=metric,
        pairs=len(values),
        baseline_mean=mean(left for left, _ in values),
        candidate_mean=mean(right for _, right in values),
        effect=effect,
        p_value=p_value,
        significant=p_value < alpha,
        direction=direction,
        method="paired-exact-sign-test",
        notes=[] if nonzero else ["All paired observations are equal."],
    )


def _two_sided_binomial(smaller_side: int, n: int) -> float:
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, index) for index in range(smaller_side + 1)) / (2**n)
    return float(min(1.0, 2 * tail))


def _overall_verdict(
    results: list[AssayMetricResult],
    *,
    matched_pairs: int,
    minimum_pairs: int,
    change_intent: ChangeIntentContract | None,
    reasons: list[str],
) -> Literal["NO_MATERIAL_CHANGE", "INTENDED_EVOLUTION", "REGRESSION", "INCONCLUSIVE"]:
    if matched_pairs < minimum_pairs:
        reasons.append(
            f"Only {matched_pairs} matched pairs are available; {minimum_pairs} are required."
        )
        return "INCONCLUSIVE"
    significant = [item for item in results if item.significant]
    if not significant:
        reasons.append(
            "No measured metric crossed the configured paired-test significance threshold."
        )
        return "NO_MATERIAL_CHANGE"
    if change_intent and change_intent.approved and _inside_envelope(significant, change_intent):
        reasons.append(
            "All statistically material effects remain inside the approved change-intent envelope."
        )
        return "INTENDED_EVOLUTION"
    reasons.append(
        "At least one statistically material effect is not authorised by an approved envelope."
    )
    return "REGRESSION"


def _inside_envelope(results: list[AssayMetricResult], contract: ChangeIntentContract) -> bool:
    envelopes = {item.metric: item for item in contract.accepted_tradeoffs}
    for result in results:
        if result.metric in contract.protected_metrics:
            return False
        envelope = envelopes.get(result.metric)
        if envelope is None or result.effect is None:
            return False
        if (
            envelope.maximum_absolute_change is not None
            and abs(result.effect) > envelope.maximum_absolute_change
        ):
            return False
        if (
            result.effect > 0
            and envelope.maximum_increase is not None
            and result.effect > envelope.maximum_increase
        ):
            return False
        if (
            result.effect < 0
            and envelope.maximum_decrease is not None
            and abs(result.effect) > envelope.maximum_decrease
        ):
            return False
        if (
            result.effect > 0
            and envelope.maximum_increase is None
            and envelope.maximum_absolute_change is None
        ):
            return False
        if (
            result.effect < 0
            and envelope.maximum_decrease is None
            and envelope.maximum_absolute_change is None
        ):
            return False
    return True


def _stage_attribution(
    pairs: list[tuple[GenerationRunRecord, GenerationRunRecord]],
) -> StageAttribution:
    order = [
        "requirements",
        "foundation",
        "architecture",
        "capabilities",
        "negotiation",
        "sml",
        "sir",
        "generated_tree",
        "quality_gates",
    ]
    counts: dict[str, int] = defaultdict(int)
    for left, right in pairs:
        stages = list(
            dict.fromkeys(
                order + sorted(set(left.stage_fingerprints) | set(right.stage_fingerprints))
            )
        )
        for stage in stages:
            if left.stage_fingerprints.get(stage) != right.stage_fingerprints.get(stage):
                counts[stage] += 1
                break
    first = None
    if counts:
        first = sorted(
            counts,
            key=lambda stage: (
                -counts[stage],
                order.index(stage) if stage in order else len(order),
                stage,
            ),
        )[0]
    return StageAttribution(
        first_changed_stage=first,
        changed_stage_counts=dict(sorted(counts.items())),
        examined_pairs=len(pairs),
    )


def _slice_results(
    pairs: list[tuple[GenerationRunRecord, GenerationRunRecord]],
    metrics: list[str],
    *,
    alpha: float,
    minimum_pairs: int,
    change_intent: ChangeIntentContract | None,
    slice_keys: list[str],
) -> list[SliceAssayResult]:
    results: list[SliceAssayResult] = []
    for slice_key in slice_keys:
        values = sorted({left.slices[slice_key] for left, _ in pairs if slice_key in left.slices})
        for value in values:
            subset = [
                (left, right)
                for left, right in pairs
                if left.slices.get(slice_key) == value and right.slices.get(slice_key) == value
            ]
            if not subset:
                continue
            metric_results = [_assay_metric(metric, subset, alpha) for metric in metrics]
            reasons: list[str] = []
            verdict = _overall_verdict(
                metric_results,
                matched_pairs=len(subset),
                minimum_pairs=minimum_pairs,
                change_intent=change_intent,
                reasons=reasons,
            )
            results.append(
                SliceAssayResult(
                    slice_key=slice_key,
                    slice_value=str(value),
                    verdict=verdict,
                    metrics=metric_results,
                )
            )
    return results
