from __future__ import annotations

from ssm.models import Candidate, Fact, SIRGraph


def build_latent_candidates(graph: SIRGraph) -> dict[str, list[Candidate]]:
    """Create deterministic candidate pools for MVP dimensions."""
    facts = set(graph.facts)
    database = next((f.args[0] for f in facts if f.predicate == "Database" and f.args), "Inmemory")
    return {
        "backend_architecture": [
            Candidate(
                id="single_file",
                label="Single file FastAPI app",
                dimension="backend_architecture",
                score=0.10,
                facts=[Fact(predicate="Candidate", args=("SingleFile",))],
                payload={"architecture": "single_file"},
            ),
            Candidate(
                id="router_service_repository",
                label="Router/service/repository layers",
                dimension="backend_architecture",
                score=0.95,
                facts=[Fact(predicate="Candidate", args=("RouterServiceRepository",))],
                payload={"architecture": "router_service_repository"},
            ),
        ],
        "python_import_style": [
            Candidate(
                id="from_import_symbols",
                label="from module import symbols",
                dimension="python_import_style",
                score=0.90,
                facts=[Fact(predicate="Candidate", args=("FromImportSymbols",))],
                payload={"style": "from_import"},
            ),
            Candidate(
                id="module_import",
                label="import module",
                dimension="python_import_style",
                score=0.65,
                facts=[Fact(predicate="Candidate", args=("ModuleImport",))],
                payload={"style": "module_import"},
            ),
        ],
        "error_handling_policy": [
            Candidate(
                id="specific_http_exceptions",
                label="Specific HTTP/domain exception mapping",
                dimension="error_handling_policy",
                score=0.95,
                facts=[Fact(predicate="Candidate", args=("SpecificHttpExceptions",))],
                payload={"broad_catch": False},
            ),
            Candidate(
                id="broad_catch_exception",
                label="Catch Exception broadly",
                dimension="error_handling_policy",
                score=0.05,
                facts=[Fact(predicate="Candidate", args=("BroadCatchException",))],
                payload={"broad_catch": True},
            ),
        ],
        "id_strategy": [
            Candidate(
                id="uuid",
                label="UUID primary identifiers",
                dimension="id_strategy",
                score=0.85,
                facts=[Fact(predicate="Candidate", args=("UUIDStrategy",))],
                payload={"id_strategy": "uuid"},
            ),
            Candidate(
                id="integer",
                label="Integer primary identifiers",
                dimension="id_strategy",
                score=0.60,
                facts=[Fact(predicate="Candidate", args=("IntegerIDStrategy",))],
                payload={"id_strategy": "integer"},
            ),
        ],
        "repository_strategy": [
            Candidate(
                id="sqlalchemy",
                label="SQLAlchemy repository",
                dimension="repository_strategy",
                score=0.90 if database == "Postgresql" else 0.65,
                facts=[Fact(predicate="Candidate", args=("SQLAlchemyRepository",))],
                payload={"repository": "sqlalchemy"},
            ),
            Candidate(
                id="in_memory",
                label="In-memory repository",
                dimension="repository_strategy",
                score=0.90 if database != "Postgresql" else 0.10,
                facts=[Fact(predicate="Candidate", args=("InMemoryRepository",))],
                payload={"repository": "in_memory"},
            ),
        ],
    }
