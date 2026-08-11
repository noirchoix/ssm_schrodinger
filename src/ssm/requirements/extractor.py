from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ssm.domain_packs.registry import select_domain_packs
from ssm.foundation.planner import AppFoundationPlanner
from ssm.requirements.schemas import (
    Ambiguity,
    Contradiction,
    RequirementAssumption,
    RequirementEvidence,
    RequirementItem,
    RequirementsIR,
)

_SECTION_RE = re.compile(r"^#{1,6}\s+(?P<title>.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(?P<value>.+?)\s*$")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


class IntentRequirementsCompiler:
    """Deterministically normalize README/product prose into a typed RequirementsIR.

    The extractor is deliberately conservative. High-impact defaults are recorded
    as assumptions, while contradictions and unsupported requests remain visible.
    """

    def compile_file(self, path: str | Path) -> RequirementsIR:
        source = Path(path)
        return self.compile_text(source.read_text(encoding="utf-8"), source_name=str(source))

    def compile_text(self, text: str, source_name: str = "<memory>") -> RequirementsIR:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        lines = normalized.splitlines()
        title = self._title(lines, normalized)
        summary = self._summary(lines, normalized)
        requirements: list[RequirementItem] = []
        requirements.extend(self._stack_requirements(lines, source_name))
        requirements.extend(self._section_requirements(lines, source_name))
        requirements.extend(self._keyword_requirements(lines, source_name))
        requirements = self._dedupe(requirements)
        requirements.extend(self._inferred_domain_requirements(normalized, requirements))
        requirements = self._dedupe(requirements)
        requirements = self._drop_first_explicit_business_rule(requirements)

        contradictions = self._contradictions(requirements)
        unsupported = self._unsupported_features(normalized)
        self._mark_requirement_statuses(requirements, contradictions, unsupported)
        ambiguities, assumptions = self._ambiguities_and_assumptions(
            normalized, requirements, unsupported
        )
        packs = [pack.id for pack in select_domain_packs(normalized)]
        stack_hints = self._stack_hints(requirements)
        payload = RequirementsIR(
            source_name=source_name,
            source_sha256=self._sha256(normalized),
            title=title,
            summary=summary,
            requirements=sorted(requirements, key=lambda item: (item.kind, item.name, item.id)),
            ambiguities=sorted(ambiguities, key=lambda item: item.id),
            contradictions=sorted(contradictions, key=lambda item: item.id),
            assumptions=sorted(assumptions, key=lambda item: item.id),
            unsupported_features=sorted(set(unsupported)),
            domain_hints=sorted(dict.fromkeys(packs)),
            stack_hints=stack_hints,
        )
        payload.semantic_fingerprint = self.semantic_fingerprint(payload)
        return payload

    @staticmethod
    def _drop_first_explicit_business_rule(
        requirements: list[RequirementItem],
    ) -> list[RequirementItem]:
        """M-RQ-01: omit the first explicitly extracted business-rule requirement."""
        dropped = False
        mutated: list[RequirementItem] = []
        for item in requirements:
            if not dropped and item.kind == "business_rule" and item.origin == "explicit":
                dropped = True
                continue
            mutated.append(item)
        return mutated

    def semantic_fingerprint(self, requirements: RequirementsIR) -> str:
        canonical: dict[str, Any] = {
            "title": requirements.title,
            "requirements": [
                {
                    "kind": item.kind,
                    "name": item.name,
                    "description": item.description,
                    "priority": item.priority,
                    "origin": item.origin,
                    "status": item.status,
                    "attributes": item.attributes,
                }
                for item in sorted(
                    requirements.requirements, key=lambda value: (value.kind, value.name, value.id)
                )
            ],
            "ambiguities": [
                item.model_dump(exclude={"id"})
                for item in sorted(requirements.ambiguities, key=lambda value: value.id)
            ],
            "contradictions": [
                item.model_dump(exclude={"id"})
                for item in sorted(requirements.contradictions, key=lambda value: value.id)
            ],
            "assumptions": [
                item.model_dump(exclude={"id"})
                for item in sorted(requirements.assumptions, key=lambda value: value.id)
            ],
            "unsupported_features": sorted(requirements.unsupported_features),
            "domain_hints": sorted(requirements.domain_hints),
            "stack_hints": dict(sorted(requirements.stack_hints.items())),
        }
        return self._sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")))

    def _title(self, lines: list[str], text: str) -> str:
        for line in lines:
            match = _SECTION_RE.match(line.strip())
            if match:
                return match.group("title").strip()[:160]
        planner_title = AppFoundationPlanner().plan(text).app_name
        return planner_title[:160]

    def _summary(self, lines: list[str], text: str) -> str:
        paragraph: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or _BULLET_RE.match(stripped):
                if paragraph:
                    break
                continue
            paragraph.append(stripped)
            if len(" ".join(paragraph)) >= 280:
                break
        return (" ".join(paragraph) or text[:300]).strip()[:500]

    def _stack_requirements(self, lines: list[str], source_name: str) -> list[RequirementItem]:
        patterns = {
            "FastAPI": ("stack", [r"\bfastapi\b"]),
            "PostgreSQL": ("stack", [r"\bpostgres(?:ql)?\b"]),
            "InMemory": ("stack", [r"\bin[- ]?memory\b"]),
            "JWT": ("security", [r"\bjwt\b", r"bearer token"]),
            "NoAuthentication": ("security", [r"\bno authentication\b", r"\bpublic api\b"]),
            "MultiTenant": ("capability", [r"multi[- ]tenant", r"tenant isolation"]),
            "SingleTenant": ("constraint", [r"single[- ]tenant"]),
        }
        result: list[RequirementItem] = []
        for line_number, line in enumerate(lines, start=1):
            lower = line.lower()
            for name, (kind, expressions) in patterns.items():
                if any(re.search(expression, lower) for expression in expressions):
                    result.append(
                        self._item(
                            kind=kind,
                            name=name,
                            description=line.strip(),
                            origin="explicit",
                            source_name=source_name,
                            line_number=line_number,
                        )
                    )
        return result

    def _section_requirements(self, lines: list[str], source_name: str) -> list[RequirementItem]:
        section = ""
        result: list[RequirementItem] = []
        section_kinds = {
            "roles": "actor",
            "users": "actor",
            "actors": "actor",
            "entities": "entity",
            "models": "entity",
            "data model": "entity",
            "workflows": "workflow",
            "business rules": "business_rule",
            "rules": "business_rule",
            "integrations": "integration",
            "reports": "report",
            "non-functional requirements": "nonfunctional",
            "nonfunctional requirements": "nonfunctional",
            "constraints": "constraint",
            "use cases": "use_case",
            "features": "capability",
        }
        for line_number, line in enumerate(lines, start=1):
            heading = _SECTION_RE.match(line.strip())
            if heading:
                section = heading.group("title").strip().lower().rstrip(":")
                continue
            bullet = _BULLET_RE.match(line)
            if not bullet:
                continue
            kind = next((value for key, value in section_kinds.items() if key in section), None)
            if kind is None:
                continue
            value = self._clean_name(bullet.group("value"))
            if not value:
                continue
            result.append(
                self._item(
                    kind=kind,
                    name=self._pascal_name(value) if kind in {"actor", "entity"} else value,
                    description=bullet.group("value").strip(),
                    origin="explicit",
                    source_name=source_name,
                    line_number=line_number,
                )
            )
        return result

    def _keyword_requirements(self, lines: list[str], source_name: str) -> list[RequirementItem]:
        capabilities = {
            "BackgroundJobs": ["background job", "worker", "queue", "celery", "asynchronous"],
            "Notifications": ["notification", "notify", "email alert"],
            "Idempotency": ["idempotency", "idempotent"],
            "Webhooks": ["webhook"],
            "Observability": ["observability", "metrics", "tracing", "structured logging"],
            "SoftDeleteRetention": ["soft delete", "retention", "data retention"],
            "Audit": ["audit log", "audit trail", "auditing"],
            "Workflow": ["workflow", "approval", "approve", "reject"],
            "RBAC": ["rbac", "role-based", "permissions"],
            "CRUD": ["crud", "create, read, update", "list, create, update"],
        }
        result: list[RequirementItem] = []
        for line_number, line in enumerate(lines, start=1):
            lower = line.lower()
            for name, tokens in capabilities.items():
                if any(token in lower for token in tokens):
                    result.append(
                        self._item(
                            kind="capability",
                            name=name,
                            description=line.strip(),
                            origin="explicit",
                            source_name=source_name,
                            line_number=line_number,
                        )
                    )
            if any(
                token in lower for token in ["must be scalable", "high availability", "low latency"]
            ):
                result.append(
                    self._item(
                        kind="nonfunctional",
                        name="PerformanceAndAvailability",
                        description=line.strip(),
                        origin="explicit",
                        source_name=source_name,
                        line_number=line_number,
                    )
                )
        return result

    def _inferred_domain_requirements(
        self, text: str, existing: list[RequirementItem]
    ) -> list[RequirementItem]:
        planner = AppFoundationPlanner().plan(text)
        existing_names = {(item.kind, item.name.lower()) for item in existing}
        inferred: list[RequirementItem] = []
        for entity in planner.entities:
            key = ("entity", entity.name.lower())
            if key not in existing_names:
                inferred.append(
                    self._item(
                        kind="entity",
                        name=entity.name,
                        description=f"Inferred from selected domain pack: {entity.name}",
                        origin="inferred",
                    )
                )
        for role in planner.roles:
            name = self._pascal_name(role.name)
            key = ("actor", name.lower())
            if key not in existing_names:
                inferred.append(
                    self._item(
                        kind="actor",
                        name=name,
                        description=f"Inferred role from selected domain pack: {role.name}",
                        origin="inferred",
                    )
                )
        for workflow in planner.workflows:
            key = ("workflow", workflow.name.lower())
            if key not in existing_names:
                inferred.append(
                    self._item(
                        kind="workflow",
                        name=workflow.name,
                        description=f"Inferred workflow for {workflow.entity}",
                        origin="inferred",
                        attributes={"entity": workflow.entity},
                    )
                )
        return inferred

    def _contradictions(self, requirements: list[RequirementItem]) -> list[Contradiction]:
        by_name = {item.name: item for item in requirements}
        pairs = [
            ("PostgreSQL", "InMemory", "Database strategy"),
            ("JWT", "NoAuthentication", "Authentication strategy"),
            ("MultiTenant", "SingleTenant", "Tenancy model"),
        ]
        contradictions: list[Contradiction] = []
        for left, right, topic in pairs:
            if left in by_name and right in by_name:
                contradictions.append(
                    Contradiction(
                        id=self._stable_id("ctr", topic, left, right),
                        topic=topic,
                        description=f"The source requests both {left} and {right}.",
                        requirement_ids=[by_name[left].id, by_name[right].id],
                    )
                )
        return contradictions

    def _unsupported_features(self, text: str) -> list[str]:
        lower = text.lower()
        unsupported = {
            "native mobile client": ["native mobile", "ios app", "android app"],
            "payment processing": ["stripe", "payment gateway", "card payments"],
            "machine-learning model training": ["train a model", "model training", "fine-tuning"],
            "blockchain runtime": ["blockchain", "smart contract"],
            "real-time geospatial dispatch": [
                "uber-like",
                "real-time dispatch",
                "geospatial matching",
            ],
        }
        return [
            name for name, tokens in unsupported.items() if any(token in lower for token in tokens)
        ]

    def _mark_requirement_statuses(
        self,
        requirements: list[RequirementItem],
        contradictions: list[Contradiction],
        unsupported: list[str],
    ) -> None:
        contradicted = {req_id for item in contradictions for req_id in item.requirement_ids}
        for item in requirements:
            if item.id in contradicted:
                item.status = "contradictory"
            elif any(feature.lower() in item.description.lower() for feature in unsupported):
                item.status = "unsupported"

    def _ambiguities_and_assumptions(
        self,
        text: str,
        requirements: list[RequirementItem],
        unsupported: list[str],
    ) -> tuple[list[Ambiguity], list[RequirementAssumption]]:
        names = {item.name for item in requirements}
        ambiguities: list[Ambiguity] = []
        assumptions: list[RequirementAssumption] = []
        if "PostgreSQL" not in names and "InMemory" not in names:
            ambiguities.append(
                Ambiguity(
                    id=self._stable_id("amb", "database"),
                    topic="Database strategy",
                    description="No persistence strategy was stated.",
                    impact="medium",
                    options=["PostgreSQL", "InMemory"],
                )
            )
            assumptions.append(
                RequirementAssumption(
                    id=self._stable_id("asm", "database", "InMemory"),
                    statement="Use InMemory persistence for the bounded baseline unless PostgreSQL is requested.",
                    source="compiler_default",
                )
            )
        if "JWT" not in names and "NoAuthentication" not in names:
            ambiguities.append(
                Ambiguity(
                    id=self._stable_id("amb", "authentication"),
                    topic="Authentication strategy",
                    description="Authentication behavior was not stated.",
                    impact="high",
                    blocking=False,
                    options=["JWT", "NoAuthentication"],
                )
            )
            assumptions.append(
                RequirementAssumption(
                    id=self._stable_id("asm", "authentication", "JWT"),
                    statement="Use JWT authentication because the current production target is auth-aware.",
                    impact="high",
                    source="compiler_default",
                )
            )
        explicit_entities = [
            item for item in requirements if item.kind == "entity" and item.origin == "explicit"
        ]
        inferred_entities = [
            item for item in requirements if item.kind == "entity" and item.origin == "inferred"
        ]
        lower = text.lower()
        if not explicit_entities:
            generic_fallback = {item.name for item in inferred_entities} == {"Product"} and not any(
                token in lower for token in ["product", "inventory", "stock", "sku"]
            )
            if generic_fallback or not inferred_entities:
                ambiguities.append(
                    Ambiguity(
                        id=self._stable_id("amb", "entities"),
                        topic="Domain entities",
                        description=(
                            "No explicit domain entity was stated; the generic Product fallback is "
                            "not sufficient for deterministic generation."
                        ),
                        impact="high",
                        blocking=True,
                        options=["Provide an entities/data-model section"],
                    )
                )
            else:
                entity_names = ", ".join(sorted(item.name for item in inferred_entities))
                ambiguities.append(
                    Ambiguity(
                        id=self._stable_id("amb", "inferred-entities", entity_names),
                        topic="Domain entities",
                        description=(
                            f"Domain entities were inferred from the selected pack: {entity_names}."
                        ),
                        impact="high",
                        blocking=False,
                        options=[
                            "Confirm inferred entities",
                            "Provide an explicit entities section",
                        ],
                        related_requirement_ids=[item.id for item in inferred_entities],
                    )
                )
                assumptions.append(
                    RequirementAssumption(
                        id=self._stable_id("asm", "inferred-entities", entity_names),
                        statement=f"Use inferred domain entities: {entity_names}.",
                        impact="high",
                        source="domain_pack",
                        related_requirement_ids=[item.id for item in inferred_entities],
                    )
                )
        if any(item.kind == "integration" for item in requirements) and not any(
            token in lower for token in ["timeout", "retry", "failure", "idempotency"]
        ):
            ambiguities.append(
                Ambiguity(
                    id=self._stable_id("amb", "integration-failure-semantics"),
                    topic="Integration failure semantics",
                    description="An integration is requested without timeout, retry, or idempotency behavior.",
                    impact="high",
                    blocking=False,
                    options=["Declare retry/timeout/idempotency policy", "Treat as external stub"],
                )
            )
        if any(
            item.name == "PerformanceAndAvailability" for item in requirements
        ) and not re.search(
            r"\b(?:p9[59]|requests? per second|rps|milliseconds?|seconds?|availability|sla)\b",
            lower,
        ):
            ambiguities.append(
                Ambiguity(
                    id=self._stable_id("amb", "performance-targets"),
                    topic="Performance and availability targets",
                    description=(
                        "Scalability or availability is requested without measurable latency, "
                        "throughput, or uptime targets."
                    ),
                    impact="high",
                    blocking=False,
                    options=[
                        "Declare p95 latency and throughput",
                        "Accept baseline load-smoke gates",
                    ],
                )
            )
        for feature in unsupported:
            assumptions.append(
                RequirementAssumption(
                    id=self._stable_id("asm", "unsupported", feature),
                    statement=f"{feature} remains outside deterministic target generation.",
                    impact="high",
                    source="inference",
                )
            )
        return ambiguities, assumptions

    def _stack_hints(self, requirements: list[RequirementItem]) -> dict[str, str]:
        names = {item.name for item in requirements}
        result: dict[str, str] = {"backend": "FastAPI"}
        if "PostgreSQL" in names:
            result["database"] = "PostgreSQL"
        elif "InMemory" in names:
            result["database"] = "InMemory"
        if "JWT" in names:
            result["auth"] = "JWT"
        elif "NoAuthentication" in names:
            result["auth"] = "None"
        return result

    def _item(
        self,
        *,
        kind: str,
        name: str,
        description: str,
        origin: str,
        source_name: str = "<inference>",
        line_number: int | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> RequirementItem:
        item_id = self._stable_id("req", kind, name, description)
        evidence = []
        if line_number is not None:
            evidence.append(
                RequirementEvidence(
                    source_id=source_name,
                    line_start=line_number,
                    line_end=line_number,
                    excerpt=description[:240],
                )
            )
        return RequirementItem(
            id=item_id,
            kind=kind,  # type: ignore[arg-type]
            name=name,
            description=description,
            origin=origin,  # type: ignore[arg-type]
            attributes=attributes or {},
            evidence=evidence,
        )

    def _dedupe(self, requirements: list[RequirementItem]) -> list[RequirementItem]:
        selected: dict[tuple[str, str], RequirementItem] = {}
        origin_rank = {"explicit": 3, "inferred": 2, "default": 1}
        for item in requirements:
            key = (item.kind, item.name.lower())
            current = selected.get(key)
            if current is None or origin_rank[item.origin] > origin_rank[current.origin]:
                selected[key] = item
            elif current is not None:
                current.evidence.extend(item.evidence)
        return list(selected.values())

    def _clean_name(self, value: str) -> str:
        cleaned = value.split(":", 1)[0].strip().strip("`*_ ")
        return re.sub(r"\s+", " ", cleaned)[:120]

    def _pascal_name(self, value: str) -> str:
        words = _WORD_RE.findall(value)
        return "".join(word[:1].upper() + word[1:] for word in words) or "Resource"

    def _stable_id(self, prefix: str, *parts: str) -> str:
        digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]
        return f"{prefix}-{digest}"

    def _sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
