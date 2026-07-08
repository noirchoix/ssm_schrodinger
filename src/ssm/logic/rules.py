from __future__ import annotations

from ssm.models import Fact, Rule


def builtin_rules() -> list[Rule]:
    """Built-in v1 Horn rules for the FastAPI MVP target."""
    return [
        Rule(
            id="RouteBodyRequiresSchema",
            when=[Fact(predicate="Route", args=("$r",)), Fact(predicate="Body", args=("$r", "$s"))],
            then=Fact(predicate="Requires", args=("Schema:$s",)),
            source="builtin.fastapi",
        ),
        Rule(
            id="RouteReturnsRequiresSchema",
            when=[
                Fact(predicate="Route", args=("$r",)),
                Fact(predicate="Returns", args=("$r", "$s")),
            ],
            then=Fact(predicate="Requires", args=("Schema:$s",)),
            source="builtin.fastapi",
        ),
        Rule(
            id="AuthRouteRequiresCurrentUserDependency",
            when=[Fact(predicate="AuthRequired", args=("$r",))],
            then=Fact(predicate="Requires", args=("Dependency:CurrentUser",)),
            source="builtin.fastapi",
        ),
        Rule(
            id="FastAPIAuthRequiresSecurityModule",
            when=[
                Fact(predicate="Target", args=("PythonFastAPI",)),
                Fact(predicate="Requires", args=("Dependency:CurrentUser",)),
            ],
            then=Fact(predicate="Requires", args=("Module:app.core.security",)),
            source="builtin.fastapi",
        ),
        Rule(
            id="PostgresRequiresSQLAlchemy",
            when=[Fact(predicate="Database", args=("Postgresql",))],
            then=Fact(predicate="Requires", args=("Dependency:SQLAlchemy",)),
            source="builtin.fastapi",
        ),
        Rule(
            id="PostgresRequiresDatabaseURL",
            when=[Fact(predicate="Database", args=("Postgresql",))],
            then=Fact(predicate="Requires", args=("EnvVar:DATABASE_URL",)),
            source="builtin.fastapi",
        ),
        Rule(
            id="UniqueRequiresDatabaseConstraint",
            when=[Fact(predicate="Unique", args=("$m", "$f"))],
            then=Fact(predicate="Requires", args=("DatabaseConstraint:unique:$m.$f",)),
            source="builtin.fastapi",
        ),
        Rule(
            id="BroadCatchForbidden",
            when=[
                Fact(predicate="Policy", args=("ForbidBroadCatch",)),
                Fact(predicate="Candidate", args=("BroadCatchException",)),
            ],
            then=Fact(predicate="Invalid", args=("Candidate:BroadCatchException",)),
            severity="error",
            source="builtin.policy",
        ),
        Rule(
            id="PostgresRejectsInMemoryRepository",
            when=[
                Fact(predicate="Database", args=("Postgresql",)),
                Fact(predicate="Candidate", args=("InMemoryRepository",)),
            ],
            then=Fact(predicate="Invalid", args=("Candidate:InMemoryRepository",)),
            severity="error",
            source="builtin.policy",
        ),
        Rule(
            id="LayeredArchitectureRejectsSingleFile",
            when=[
                Fact(predicate="Policy", args=("LayeredArchitecture",)),
                Fact(predicate="Candidate", args=("SingleFile",)),
            ],
            then=Fact(predicate="Invalid", args=("Candidate:SingleFile",)),
            severity="error",
            source="builtin.policy",
        ),
    ]
