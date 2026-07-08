from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from ssm.errors import CompilerDiagnostic, SemanticError
from ssm.models import Fact, ProofObject, ProofStatus, Rule

Substitution = dict[str, str]


@dataclass(frozen=True)
class ClosureResult:
    facts: frozenset[Fact]
    proofs: tuple[ProofObject, ...]
    invalid_facts: tuple[Fact, ...]


class LogicEngine:
    """Small deterministic Horn-style forward-chaining engine.

    This is intentionally not a full theorem prover. It implements the MVP
    symbolic decision layer required by the v1.1 architecture: facts, rules,
    derived requirements, invalid-state detection, and proof traces.
    """

    def __init__(self, rules: Iterable[Rule]):
        self.rules = sorted(list(rules), key=lambda r: r.id)

    def closure(self, initial_facts: Iterable[Fact]) -> ClosureResult:
        facts: set[Fact] = set(initial_facts)
        proof_map: dict[Fact, ProofObject] = {}
        for f in facts:
            proof_map[f] = ProofObject(
                decision_id=f"fact.{str(f)}",
                claim=str(f),
                status=ProofStatus.proved,
                support=["asserted"],
            )
        changed = True
        while changed:
            changed = False
            for rule in self.rules:
                for subst, support in self._match_rule(rule, facts):
                    derived = self._instantiate(rule.then, subst)
                    if derived not in facts:
                        facts.add(derived)
                        changed = True
                        proof_map[derived] = ProofObject(
                            decision_id=f"rule.{rule.id}.{str(derived)}",
                            claim=str(derived),
                            status=ProofStatus.proved
                            if derived.predicate != "Invalid"
                            else ProofStatus.rejected,
                            support=[*(str(s) for s in support), f"Rule:{rule.id}"],
                            source=rule.source,
                        )
        invalids = tuple(sorted([f for f in facts if f.predicate == "Invalid"], key=str))
        proofs = tuple(proof_map[f] for f in sorted(proof_map, key=str))
        return ClosureResult(facts=frozenset(facts), proofs=proofs, invalid_facts=invalids)

    def check_required_artifacts(self, closure: ClosureResult) -> None:
        diagnostics: list[CompilerDiagnostic] = []
        artifacts = {f.args[0] for f in closure.facts if f.predicate == "Artifact" and f.args}
        for fact in sorted(closure.facts, key=str):
            if fact.predicate != "Requires" or not fact.args:
                continue
            req = fact.args[0]
            if req.startswith("Schema:") and req not in artifacts:
                schema = req.split(":", 1)[1]
                diagnostics.append(
                    CompilerDiagnostic(
                        code="LOG201",
                        message=f"Logic requires schema {schema}, but no matching artifact exists.",
                        suggested_fix=f"Define #DataModel {schema} or remove the route reference.",
                    )
                )
        if diagnostics:
            raise SemanticError(diagnostics)

    def check_admissibility(
        self, base_facts: Iterable[Fact], candidate_facts: Iterable[Fact], decision_id: str
    ) -> tuple[bool, ProofObject, ClosureResult]:
        initial = list(base_facts) + list(candidate_facts)
        closure = self.closure(initial)
        if closure.invalid_facts:
            proof = ProofObject(
                decision_id=decision_id,
                claim="Candidate admissibility",
                status=ProofStatus.rejected,
                support=[str(f) for f in closure.invalid_facts],
                source="logic.admissibility",
            )
            return False, proof, closure
        proof = ProofObject(
            decision_id=decision_id,
            claim="Candidate admissibility",
            status=ProofStatus.admissible,
            support=["No Invalid(...) facts derived under candidate assumptions."],
            source="logic.admissibility",
        )
        return True, proof, closure

    def _match_rule(self, rule: Rule, facts: set[Fact]) -> list[tuple[Substitution, list[Fact]]]:
        states: list[tuple[Substitution, list[Fact]]] = [({}, [])]
        facts_by_pred: dict[str, list[Fact]] = defaultdict(list)
        for f in facts:
            facts_by_pred[f.predicate].append(f)
        for pattern in rule.when:
            next_states: list[tuple[Substitution, list[Fact]]] = []
            for subst, support in states:
                for fact in facts_by_pred.get(pattern.predicate, []):
                    new_subst = self._unify(pattern, fact, subst)
                    if new_subst is not None:
                        next_states.append((new_subst, support + [fact]))
            states = next_states
            if not states:
                return []
        # Deterministic ordering by substitution and support.
        return sorted(states, key=lambda s: (sorted(s[0].items()), [str(f) for f in s[1]]))

    def _unify(self, pattern: Fact, fact: Fact, subst: Substitution) -> Substitution | None:
        if pattern.predicate != fact.predicate or len(pattern.args) != len(fact.args):
            return None
        out = dict(subst)
        for p, a in zip(pattern.args, fact.args, strict=False):
            if p.startswith("$"):
                if p in out and out[p] != a:
                    return None
                out[p] = a
            elif p != a:
                return None
        return out

    def _instantiate(self, pattern: Fact, subst: Substitution) -> Fact:
        args = []
        for arg in pattern.args:
            value = arg
            for key, replacement in sorted(subst.items(), key=lambda kv: len(kv[0]), reverse=True):
                value = value.replace(key, replacement)
            args.append(value)
        return Fact(predicate=pattern.predicate, args=tuple(args))
