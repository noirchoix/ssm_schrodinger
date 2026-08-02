from __future__ import annotations

import hashlib
import json

from ssm.capabilities.registry import all_capability_packs
from ssm.capabilities.schemas import (
    CapabilityCompositionIssue,
    CapabilityCompositionResult,
    CapabilitySelection,
    SupportStatus,
)
from ssm.foundation.schemas import AppFoundationPlan
from ssm.requirements.schemas import RequirementsIR


class CapabilityComposer:
    """Compose capability packs while preserving implementation honesty."""

    def compose(
        self, requirements: RequirementsIR, foundation: AppFoundationPlan
    ) -> CapabilityCompositionResult:
        registry = all_capability_packs()
        requested_by_id: dict[str, list[str]] = {}
        for item in requirements.requirements:
            for capability_id, pack in registry.items():
                if item.kind != "capability":
                    continue
                haystack = f"{item.name} {item.description}".lower()
                if item.name.lower() == capability_id.replace("_", "").lower() or any(
                    trigger in haystack for trigger in pack.triggers
                ):
                    requested_by_id.setdefault(capability_id, []).append(item.id)

        inferred: set[str] = {"observability"}
        if foundation.roles:
            inferred.add("rbac")
        if foundation.tenant_enabled:
            inferred.add("tenant_isolation")
        if foundation.audit_enabled:
            inferred.add("audit")
        if foundation.workflows:
            inferred.add("workflow")

        selected_ids = set(requested_by_id) | inferred
        added = True
        while added:
            added = False
            for capability_id in list(selected_ids):
                pack = registry[capability_id]
                for prerequisite in pack.prerequisites:
                    if prerequisite not in selected_ids:
                        selected_ids.add(prerequisite)
                        inferred.add(prerequisite)
                        added = True

        issues: list[CapabilityCompositionIssue] = []
        selections: list[CapabilitySelection] = []
        for capability_id in sorted(selected_ids):
            pack = registry[capability_id]
            conflicts = sorted(set(pack.conflicts) & selected_ids)
            for conflict in conflicts:
                issues.append(
                    CapabilityCompositionIssue(
                        code="CAP_PACK_CONFLICT",
                        capability_id=capability_id,
                        message=f"{capability_id} conflicts with selected capability {conflict}.",
                        severity="error",
                    )
                )
            support_status: SupportStatus
            if pack.implementation_status == "production":
                support_status = "SUPPORTED"
                limitations: list[str] = []
            elif pack.implementation_status in {"scaffold", "contract_only"}:
                support_status = "PARTIALLY_SUPPORTED"
                limitations = [
                    f"{capability_id} is {pack.implementation_status}; its full runtime is not generated."
                ]
                issues.append(
                    CapabilityCompositionIssue(
                        code="CAP_PACK_PARTIAL_IMPLEMENTATION",
                        capability_id=capability_id,
                        message=limitations[0],
                        severity="warning",
                    )
                )
            else:
                support_status = "UNSUPPORTED"
                limitations = [f"{capability_id} is unsupported by the current target pack."]
                issues.append(
                    CapabilityCompositionIssue(
                        code="CAP_PACK_UNSUPPORTED",
                        capability_id=capability_id,
                        message=limitations[0],
                        severity="error",
                    )
                )
            selections.append(
                CapabilitySelection(
                    capability_id=capability_id,
                    requested=capability_id in requested_by_id,
                    inferred=capability_id in inferred and capability_id not in requested_by_id,
                    implementation_status=pack.implementation_status,
                    support_status=support_status,
                    guarantees=pack.guarantees,
                    assumptions=pack.assumptions,
                    limitations=limitations,
                    required_tests=pack.required_tests,
                    required_evidence=pack.required_evidence,
                    requirement_ids=sorted(requested_by_id.get(capability_id, [])),
                )
            )

        status: SupportStatus
        if any(issue.severity == "error" for issue in issues):
            status = "UNSUPPORTED"
        elif any(item.support_status == "PARTIALLY_SUPPORTED" for item in selections):
            status = "PARTIALLY_SUPPORTED"
        elif any(item.assumptions for item in selections):
            status = "SUPPORTED_WITH_ASSUMPTIONS"
        else:
            status = "SUPPORTED"
        result = CapabilityCompositionResult(
            status=status,
            selected=selections,
            issues=issues,
            guarantees=sorted({value for item in selections for value in item.guarantees}),
            assumptions=sorted({value for item in selections for value in item.assumptions}),
            limitations=sorted({value for item in selections for value in item.limitations}),
        )
        result.semantic_fingerprint = self._fingerprint(result)
        return result

    def _fingerprint(self, result: CapabilityCompositionResult) -> str:
        payload = result.model_dump(exclude={"semantic_fingerprint"})
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
