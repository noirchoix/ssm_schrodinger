from __future__ import annotations

from ssm.errors import CompilerDiagnostic, ResolutionError
from ssm.logic.engine import LogicEngine
from ssm.models import LatentChoice, ResolutionResult, SIRGraph
from ssm.resolver.candidates import build_latent_candidates


class LatentResolver:
    """Hard-filter candidates through logic, then soft-score and deterministically collapse."""

    def __init__(self, logic_engine: LogicEngine):
        self.logic_engine = logic_engine

    def resolve(self, graph: SIRGraph) -> ResolutionResult:
        candidate_pools = build_latent_candidates(graph)
        selected = {}
        choices: list[LatentChoice] = []
        proof_trace = []
        current_facts = list(graph.facts)
        self.logic_engine.closure(current_facts)

        for dimension in sorted(candidate_pools):
            candidates = sorted(candidate_pools[dimension], key=lambda c: c.id)
            choice = LatentChoice(
                id=f"choice.{dimension}", dimension=dimension, candidates=candidates
            )
            admissible = []
            for candidate in candidates:
                ok, proof, closure = self.logic_engine.check_admissibility(
                    current_facts,
                    candidate.facts,
                    decision_id=f"{dimension}.{candidate.id}",
                )
                if ok:
                    admissible.append((candidate, proof, closure))
                else:
                    choice.rejected.append(proof)
                    proof_trace.append(proof)
            if not admissible:
                raise ResolutionError(
                    [
                        CompilerDiagnostic(
                            code="RES001",
                            message=f"No admissible candidates for latent choice {dimension}.",
                            suggested_fix="Relax constraints or add a compatible target-pack rule.",
                        )
                    ]
                )
            # Soft scoring among only admissible candidates. Stable tie-break by id.
            admissible.sort(key=lambda item: (-item[0].score, item[0].id))
            winner, proof, closure = admissible[0]
            choice.selected_candidate_id = winner.id
            choice.proof = proof
            selected[dimension] = winner
            proof_trace.append(proof)
            current_facts.extend(winner.facts)
            choices.append(choice)

        final_closure = self.logic_engine.closure(current_facts)
        return ResolutionResult(
            choices=choices,
            selected=selected,
            proof_trace=proof_trace + list(final_closure.proofs),
            facts=sorted(final_closure.facts, key=str),
        )
