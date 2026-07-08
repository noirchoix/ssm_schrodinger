from __future__ import annotations

import re

from ssm.agents.schemas import FeatureRequirement, ProjectRequirements


class IntentAgent:
    """Conservative deterministic intent extractor for offline drafting."""

    def extract(self, prompt: str) -> ProjectRequirements:
        lower = prompt.lower()
        name = self._name(prompt)
        features = []
        for word in [
            "auth",
            "jwt",
            "crud",
            "api",
            "dashboard",
            "database",
            "postgresql",
            "products",
            "todos",
            "suppliers",
            "workflow",
            "approval",
            "tenant",
            "audit",
            "hr",
            "expense",
            "crm",
            "ticketing",
            "school",
        ]:
            if word in lower:
                features.append(
                    FeatureRequirement(
                        name=word.title(), description=f"Detected from prompt: {word}"
                    )
                )
        hints = {}
        if "fastapi" in lower or "api" in lower:
            hints["backend"] = "FastAPI"
        if "postgres" in lower or "saas" in lower:
            hints["database"] = "PostgreSQL"
        if "jwt" in lower or "auth" in lower:
            hints["auth"] = "JWT"
        domain = self._domain(lower)
        return ProjectRequirements(
            project_name=name,
            description=prompt,
            domain=domain,
            features=features,
            stack_hints=hints,
        )

    def _name(self, prompt: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", prompt)
        important = [w for w in words if w.lower() not in {"build", "a", "an", "the", "with"}]
        return " ".join(important[:4]).title() or "Generated Project"

    def _domain(self, lower: str) -> str | None:
        for domain in ["hr", "expense", "crm", "ticketing", "school", "inventory", "procurement"]:
            if domain in lower:
                return domain
        if "leave" in lower or "employee" in lower:
            return "hr"
        if "ticket" in lower or "helpdesk" in lower:
            return "ticketing"
        return None
