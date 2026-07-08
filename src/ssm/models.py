from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)


class SourceRange(FrozenModel):
    file: str
    start_line: int
    end_line: int
    start_col: int | None = None
    end_col: int | None = None


class Directive(BaseModel):
    name: str
    args: str | None = None
    source_range: SourceRange


class SMLSection(BaseModel):
    section_type: str
    name: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)
    source_range: SourceRange


class SMLDocument(BaseModel):
    source_file: str
    directives: list[Directive] = Field(default_factory=list)
    sections: list[SMLSection] = Field(default_factory=list)

    def sections_of_type(self, section_type: str) -> list[SMLSection]:
        wanted = section_type.lower()
        return [s for s in self.sections if s.section_type.lower() == wanted]


class EvidenceRef(BaseModel):
    source_type: Literal[
        "user", "sml", "docs", "compiler_default", "target_pack", "logic", "resolver"
    ]
    source_id: str
    summary: str


class SIRNode(BaseModel):
    id: str
    node_type: str
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    source_range: SourceRange | None = None
    provenance: list[EvidenceRef] = Field(default_factory=list)


class SIRGraph(BaseModel):
    nodes: list[SIRNode] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)

    def by_type(self, node_type: str) -> list[SIRNode]:
        wanted = node_type.lower()
        return [n for n in self.nodes if n.node_type.lower() == wanted]

    def node_by_id(self, node_id: str) -> SIRNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)


class Fact(FrozenModel):
    predicate: str
    args: tuple[str, ...] = Field(default_factory=tuple)

    @classmethod
    def parse(cls, text: str) -> Fact:
        text = text.strip()
        if not text:
            raise ValueError("empty fact")
        if "(" not in text or not text.endswith(")"):
            return cls(predicate=text, args=())
        pred, rest = text.split("(", 1)
        inner = rest[:-1].strip()
        args: list[str] = []
        if inner:
            depth = 0
            current: list[str] = []
            for ch in inner:
                if ch == "," and depth == 0:
                    args.append("".join(current).strip())
                    current = []
                else:
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                    current.append(ch)
            if current:
                args.append("".join(current).strip())
        return cls(predicate=pred.strip(), args=tuple(args))

    def __str__(self) -> str:
        if not self.args:
            return self.predicate
        return f"{self.predicate}({', '.join(self.args)})"

    def stable_key(self) -> tuple[str, tuple[str, ...]]:
        return (self.predicate, self.args)


class Rule(BaseModel):
    id: str
    when: list[Fact]
    then: Fact
    severity: Literal["info", "warning", "error"] = "info"
    source: str = "builtin"


class ProofStatus(StrEnum):
    proved = "proved"
    rejected = "rejected"
    admissible = "admissible"
    error = "error"


class ProofObject(BaseModel):
    decision_id: str
    claim: str
    status: ProofStatus
    support: list[str] = Field(default_factory=list)
    source: str | None = None


class Candidate(BaseModel):
    id: str
    label: str
    dimension: str
    facts: list[Fact] = Field(default_factory=list)
    score: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)


class LatentChoice(BaseModel):
    id: str
    dimension: str
    candidates: list[Candidate] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    rejected: list[ProofObject] = Field(default_factory=list)
    proof: ProofObject | None = None


class ResolutionResult(BaseModel):
    choices: list[LatentChoice] = Field(default_factory=list)
    selected: dict[str, Candidate] = Field(default_factory=dict)
    proof_trace: list[ProofObject] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)


class GeneratedFile(BaseModel):
    path: str
    content: str
    source_map: dict[str, Any] = Field(default_factory=dict)


class CompileManifest(BaseModel):
    compiler_version: str
    target: str
    sml_hash: str
    sir_hash: str
    resolved_ir_hash: str
    generated_files: list[str]
    selected_candidates: dict[str, str]
    proof_count: int


class CompileResult(BaseModel):
    success: bool
    files: list[GeneratedFile] = Field(default_factory=list)
    manifest: CompileManifest | None = None
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    proof_trace: list[ProofObject] = Field(default_factory=list)
    sir: SIRGraph | None = None
    resolution: ResolutionResult | None = None
