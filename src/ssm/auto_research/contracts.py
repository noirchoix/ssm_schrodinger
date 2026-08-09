from __future__ import annotations

from typing import Any

from ssm.auto_research.schemas import (
    BehaviouralContract,
    EvaluationRun,
    GenerationRunRecord,
    MetricRule,
    RuleVerification,
)


def verify_contract(
    contract: BehaviouralContract,
    run: GenerationRunRecord,
) -> EvaluationRun:
    outcomes = [_verify_rule(rule, run) for rule in contract.rules]
    if any(item.verdict == "FAIL" for item in outcomes):
        verdict = "FAIL"
    elif any(item.verdict == "UNCHECKED" for item in outcomes):
        verdict = "UNCHECKED"
    else:
        verdict = "PASS"
    return EvaluationRun.create(
        contract_id=contract.contract_id,
        generation_run_id=run.record_id,
        verdict=verdict,
        outcomes=outcomes,
    )


def _verify_rule(rule: MetricRule, run: GenerationRunRecord) -> RuleVerification:
    observation = run.metrics.get(rule.metric)
    if observation is None or not observation.measured or observation.value is None:
        return RuleVerification(
            metric=rule.metric,
            verdict="FAIL" if rule.required else "UNCHECKED",
            observed=None,
            message=(
                "Required measured observation is absent."
                if rule.required
                else "Optional observation is absent."
            ),
        )
    observed = observation.value
    try:
        passed = _compare(observed, rule.operator, rule.threshold)
    except (TypeError, ValueError) as exc:
        return RuleVerification(
            metric=rule.metric,
            verdict="FAIL",
            observed=observed,
            message=f"Rule could not be evaluated: {exc}",
        )
    return RuleVerification(
        metric=rule.metric,
        verdict="PASS" if passed else "FAIL",
        observed=observed,
        message=(
            "Rule satisfied." if passed else f"Rule {rule.operator} {rule.threshold!r} failed."
        ),
    )


def _compare(observed: Any, operator: str, threshold: Any) -> bool:
    if operator == "present":
        return observed is not None
    if operator == "eq":
        return bool(observed == threshold)
    if operator == "ne":
        return bool(observed != threshold)
    if operator == "lt":
        return bool(observed < threshold)
    if operator == "le":
        return bool(observed <= threshold)
    if operator == "gt":
        return bool(observed > threshold)
    if operator == "ge":
        return bool(observed >= threshold)
    if operator == "between":
        if not isinstance(threshold, list) or len(threshold) != 2:
            raise ValueError("between requires a two-item threshold list")
        return bool(threshold[0] <= observed <= threshold[1])
    raise ValueError(f"Unknown metric operator: {operator}")
