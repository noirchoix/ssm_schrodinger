from __future__ import annotations

from ssm.agents.schemas import SemanticPatch


class RepairAgent:
    """Produces semantic patches instead of editing generated source directly."""

    def patch_missing_schema(self, schema_name: str) -> SemanticPatch:
        return SemanticPatch(
            target="sml",
            patch=f"\n#DataModel {schema_name}\nfields:\n  id: uuid primary\n",
            rationale=f"Compiler diagnostics indicate that {schema_name} is required but absent.",
            expected_effect="SIR will include an Artifact(Schema:...) fact and logic validation can proceed.",
        )
