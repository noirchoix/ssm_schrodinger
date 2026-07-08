from __future__ import annotations

from ssm.agents.schemas import ProjectRequirements, SMLDocumentDraft
from ssm.foundation.negotiator import CapabilityNegotiator
from ssm.foundation.planner import AppFoundationPlanner
from ssm.foundation.renderer import FoundationSMLRenderer


class SMLGeneratorAgent:
    """Creates SML drafts only. It never emits final source code."""

    def __init__(
        self,
        planner: AppFoundationPlanner | None = None,
        renderer: FoundationSMLRenderer | None = None,
        negotiator: CapabilityNegotiator | None = None,
    ):
        self.planner = planner or AppFoundationPlanner()
        self.renderer = renderer or FoundationSMLRenderer()
        self.negotiator = negotiator or CapabilityNegotiator()

    def draft(self, requirements: ProjectRequirements) -> SMLDocumentDraft:
        prompt = requirements.description or requirements.project_name
        plan = self.planner.plan(prompt)
        if requirements.project_name:
            plan.app_name = requirements.project_name
        for key, value in requirements.stack_hints.items():
            if key == "backend":
                plan.backend = value
            elif key == "database":
                plan.database = value
            elif key == "auth":
                plan.auth = value
        negotiation = self.negotiator.negotiate_plan(plan)
        text = self.renderer.render(plan)
        return SMLDocumentDraft(
            text=text,
            assumptions=[*plan.assumptions, *negotiation.assumptions],
            unresolved_questions=plan.questions,
            provenance=["agent:SMLGeneratorAgent"],
        )
