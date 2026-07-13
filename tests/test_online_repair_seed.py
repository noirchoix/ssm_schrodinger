from __future__ import annotations

import json
from pathlib import Path

from ssm.agents.settings import OnlineAgentSettings
from ssm.foundation.builder import OnlineBuildService

BAD_SEED = """#Project
name: Broken Todo Seed

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel Todo
fields:
  id: uuid primary
  title: string required max=120

#Route ListTodos
method: GET
path: /todos
auth: required
body: none
returns: Todo[]
"""


def test_seeded_initial_draft_forces_bounded_provider_repair(tmp_path: Path) -> None:
    settings = OnlineAgentSettings.from_env().with_overrides(
        agent_mode="online",
        provider="mock",
        max_retries=0,
    )
    settings = settings.model_copy(update={"run_online_ai": True})
    result = OnlineBuildService(settings).build(
        prompt="Build a todo API with CRUD.",
        out_dir=tmp_path,
        repair_attempts=2,
        initial_draft_text=BAD_SEED,
    )
    assert result.status == "ACCEPTED"
    assert result.attempts == 2
    trace = json.loads((tmp_path / "repair_trace.json").read_text(encoding="utf-8"))
    assert trace["schema_version"] == "2.0"
    assert trace["events"][0]["stage"] == "compile"
    assert trace["events"][0]["status"] == "rejected"
    assert trace["events"][-1]["status"] == "accepted"
