from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path
from pprint import pformat
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Any

from ssm import __version__
from ssm.backends.python_fastapi.platform import (
    evidence_record_files,
    platform_source_files,
    platform_test_files,
)
from ssm.models import CompileManifest, GeneratedFile, ResolutionResult, SIRGraph
from ssm.semantic.field_parser import normalize_schema_name, schema_is_list


@dataclass(frozen=True)
class RoutePlan:
    name: str
    method: str
    path: str
    auth_required: bool
    body: str | None
    returns: str | None
    returns_list: bool
    entity: str


class PythonFastAPITarget:
    """Production-oriented FastAPI target pack.

    The target intentionally keeps generation deterministic.  It emits normal Python
    source files only; no LLM-written final source is used at codegen time.
    """

    id = "python.fastapi"

    def generate(
        self,
        graph: SIRGraph,
        resolution: ResolutionResult,
        sml_hash: str,
        sir_hash: str,
        resolved_ir_hash: str,
    ) -> tuple[list[GeneratedFile], CompileManifest]:
        models = {node.name: node for node in graph.by_type("DataModel")}
        routes = [self._route_plan(node) for node in graph.by_type("Route")]
        repo_strategy = self._repo_strategy(resolution)
        entity_names = {r.entity for r in routes}
        project_name = self._project_name(graph)
        files: list[GeneratedFile] = []

        files.append(
            GeneratedFile(path="pyproject.toml", content=self._pyproject(resolution, repo_strategy))
        )
        files.append(GeneratedFile(path="README.md", content=self._readme(graph, repo_strategy)))
        files.append(
            GeneratedFile(
                path="docs/domain_foundation.md", content=self._domain_foundation_doc(graph)
            )
        )
        files.append(
            GeneratedFile(path=".env.example", content=self._env_example(resolution, project_name))
        )
        files.append(GeneratedFile(path=".gitignore", content=self._gitignore()))
        files.append(GeneratedFile(path="Dockerfile", content=self._dockerfile()))
        files.append(GeneratedFile(path=".dockerignore", content=self._dockerignore()))
        files.append(GeneratedFile(path="Makefile", content=self._makefile(repo_strategy)))
        files.append(GeneratedFile(path=".pre-commit-config.yaml", content=self._pre_commit()))
        files.append(
            GeneratedFile(path=".github/workflows/ci.yml", content=self._ci_workflow(repo_strategy))
        )
        files.append(
            GeneratedFile(path="docker-compose.yml", content=self._docker_compose(repo_strategy))
        )
        files.append(GeneratedFile(path="load/locustfile.py", content=self._locustfile(routes)))
        files.extend(platform_source_files(graph))

        files.append(GeneratedFile(path="app/__init__.py", content=""))
        files.append(
            GeneratedFile(
                path="app/main.py", content=self._main(routes, repo_strategy, project_name)
            )
        )
        files.append(GeneratedFile(path="app/core/__init__.py", content=""))
        files.append(GeneratedFile(path="app/core/config.py", content=self._config(project_name)))
        files.append(GeneratedFile(path="app/core/errors.py", content=self._errors()))
        files.append(GeneratedFile(path="app/core/logging.py", content=self._logging()))
        files.append(
            GeneratedFile(
                path="app/core/security.py",
                content=self._security(any(r.auth_required for r in routes)),
            )
        )
        files.append(GeneratedFile(path="app/middleware/__init__.py", content=""))
        files.append(
            GeneratedFile(
                path="app/middleware/request_id.py", content=self._request_id_middleware()
            )
        )
        files.append(GeneratedFile(path="app/api/__init__.py", content=""))
        files.append(GeneratedFile(path="app/api/routes/__init__.py", content=""))
        files.append(
            GeneratedFile(path="app/schemas/__init__.py", content=self._schema_init(models))
        )
        files.append(
            GeneratedFile(path="app/models/__init__.py", content=self._models_init(entity_names))
        )
        files.append(GeneratedFile(path="app/services/__init__.py", content=""))
        files.append(GeneratedFile(path="app/repositories/__init__.py", content=""))

        if repo_strategy == "sqlalchemy":
            files.append(GeneratedFile(path="app/db/__init__.py", content=""))
            files.append(GeneratedFile(path="app/db/base.py", content=self._db_base()))
            files.append(
                GeneratedFile(
                    path="app/db/session.py", content=self._db_session(sorted(entity_names))
                )
            )
            files.extend(self._alembic_files(models, entity_names))

        for model_name in sorted(models):
            model = models[model_name]
            module = self._module_name(model_name)
            files.append(
                GeneratedFile(path=f"app/schemas/{module}.py", content=self._schema_file(model))
            )
            # Only route-owned domain entities should produce persistence model files.
            # DTO/input schemas such as ProductCreate or LeaveRequestCreate are generated
            # under app/schemas only; emitting unused app/models/*_create.py files makes
            # generated apps look larger than they are and unfairly depresses coverage.
            if model_name in entity_names:
                if repo_strategy == "sqlalchemy":
                    files.append(
                        GeneratedFile(
                            path=f"app/models/{module}.py",
                            content=self._sqlalchemy_model_file(model),
                        )
                    )
                else:
                    files.append(
                        GeneratedFile(
                            path=f"app/models/{module}.py",
                            content=self._dataclass_model_file(model),
                        )
                    )
            entity_routes = [r for r in routes if r.entity == model_name]
            if entity_routes:
                files.append(
                    GeneratedFile(
                        path=f"app/repositories/{module}_repository.py",
                        content=self._repository_file(model, repo_strategy),
                    )
                )
                files.append(
                    GeneratedFile(
                        path=f"app/services/{module}_service.py",
                        content=self._service_file(model, repo_strategy),
                    )
                )
                files.append(
                    GeneratedFile(
                        path=f"app/api/routes/{module}.py",
                        content=self._routes_file(model, entity_routes, repo_strategy),
                    )
                )

        for path, content in self._test_files(graph, models, routes, repo_strategy).items():
            files.append(GeneratedFile(path=path, content=content))

        files.append(
            GeneratedFile(
                path="proof_trace.json",
                content=json.dumps(
                    [p.model_dump(mode="json") for p in resolution.proof_trace],
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
            )
        )

        files = self._canonicalize_generated_files(files)

        base_generated_names = sorted(f.path for f in files)
        provisional_manifest = CompileManifest(
            compiler_version=__version__,
            target=self.id,
            sml_hash=sml_hash,
            sir_hash=sir_hash,
            resolved_ir_hash=resolved_ir_hash,
            generated_files=base_generated_names,
            selected_candidates={k: v.id for k, v in sorted(resolution.selected.items())},
            proof_count=len(resolution.proof_trace),
        )
        evidence_files = evidence_record_files(
            graph,
            resolution,
            provisional_manifest,
            base_generated_names,
        )
        generated_names = sorted(base_generated_names + [f.path for f in evidence_files])
        manifest = CompileManifest(
            compiler_version=__version__,
            target=self.id,
            sml_hash=sml_hash,
            sir_hash=sir_hash,
            resolved_ir_hash=resolved_ir_hash,
            generated_files=generated_names,
            selected_candidates={k: v.id for k, v in sorted(resolution.selected.items())},
            proof_count=len(resolution.proof_trace),
        )
        files.extend(evidence_record_files(graph, resolution, manifest, generated_names))
        files.append(
            GeneratedFile(
                path="sml.manifest.json", content=manifest.model_dump_json(indent=2) + "\n"
            )
        )
        return sorted(files, key=lambda f: f.path), manifest

    def _canonicalize_generated_files(self, files: list[GeneratedFile]) -> list[GeneratedFile]:
        """Apply deterministic code-quality normalization to generated Python files.

        Ruff is treated as part of the Python FastAPI target pack.  The compiler still
        emits source deterministically; this pass canonicalizes formatting/import order
        so generated projects pass their own quality gates immediately.
        """
        ruff = shutil.which("ruff")
        if ruff is None:
            return files

        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for generated in files:
                target = root / generated.path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(generated.content, encoding="utf-8")

            for command in ([ruff, "check", ".", "--fix"], [ruff, "format", "."]):
                completed = subprocess.run(  # nosec B603
                    command,
                    cwd=root,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if completed.returncode != 0:
                    output = (completed.stdout + completed.stderr).strip()
                    raise RuntimeError(
                        f"Generated FastAPI project failed canonicalization with {command}:\n"
                        f"{output}"
                    )

            canonicalized: list[GeneratedFile] = []
            for generated in files:
                target = root / generated.path
                content = (
                    target.read_text(encoding="utf-8") if target.exists() else generated.content
                )
                canonicalized.append(generated.model_copy(update={"content": content}))
            return canonicalized

    def _domain_foundation_doc(self, graph: SIRGraph) -> str:
        groups = {
            "Capabilities": graph.by_type("Capability"),
            "Roles": graph.by_type("Role"),
            "Relationships": graph.by_type("Relationship"),
            "Workflows": graph.by_type("Workflow"),
            "Business Rules": graph.by_type("BusinessRule") + graph.by_type("Invariant"),
            "SaaS Primitives": graph.by_type("Tenant") + graph.by_type("Audit"),
            "Reports": graph.by_type("Report"),
        }
        lines = [
            "# Domain Foundation",
            "",
            "This file is generated from SML semantic foundation sections. It documents ",
            "the domain-neutral app foundation used by the deterministic target pack.",
            "",
        ]
        for title, nodes in groups.items():
            if not nodes:
                continue
            lines.extend([f"## {title}", ""])
            for node in sorted(nodes, key=lambda n: n.name):
                lines.append(f"- **{node.name}**")
                for key, value in sorted(node.attributes.items()):
                    lines.append(f"  - `{key}`: {value}")
            lines.append("")
        if len(lines) <= 5:
            lines.append("No domain foundation metadata was declared in this SML document.")
            lines.append("")
        return "\n".join(lines)

    def _repo_strategy(self, resolution: ResolutionResult) -> str:
        candidate = resolution.selected.get("repository_strategy")
        return candidate.id if candidate else "in_memory"

    def _project_name(self, graph: SIRGraph) -> str:
        project = next((node for node in graph.by_type("Project")), None)
        return project.name if project else "Generated SML Application"

    def _route_plan(self, node: Any) -> RoutePlan:
        method = str(node.attributes.get("method", "GET")).upper()
        path = str(node.attributes.get("path", "/"))
        auth = str(node.attributes.get("auth", "")).lower() in {
            "required",
            "admin",
            "authenticated",
            "user",
            "true",
        }
        body = (
            normalize_schema_name(str(node.attributes.get("body")))
            if node.attributes.get("body")
            else None
        )
        returns_raw = (
            str(node.attributes.get("returns")) if node.attributes.get("returns") else None
        )
        returns = normalize_schema_name(returns_raw) if returns_raw else None
        returns_list = schema_is_list(returns_raw) if returns_raw else False
        entity = self._infer_entity(path, body, returns)
        return RoutePlan(
            name=node.name,
            method=method,
            path=path,
            auth_required=auth,
            body=body,
            returns=returns,
            returns_list=returns_list,
            entity=entity,
        )

    def _infer_entity(self, path: str, body: str | None, returns: str | None) -> str:
        if returns and returns not in {"None", "null"}:
            return returns.removesuffix("Create").removesuffix("Update")
        if body:
            return body.removesuffix("Create").removesuffix("Update")
        token = path.strip("/").split("/")[0] or "Resource"
        return self._class_name(token[:-1] if token.endswith("s") else token)

    def _module_name(self, name: str) -> str:
        s = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s)
        return re.sub(r"[^a-zA-Z0-9_]+", "_", s).lower().strip("_")

    def _class_name(self, text: str) -> str:
        return (
            "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", text) if part)
            or "Resource"
        )

    def _schema_file(self, model: Any) -> str:
        fields = model.attributes.get("fields", [])
        stdlib_imports: list[str] = []
        if any(f["python_type"] == "UUID" for f in fields):
            stdlib_imports.append("from uuid import UUID")
        if any(f["python_type"] == "datetime" for f in fields):
            stdlib_imports.append("from datetime import datetime")
        if any(f["python_type"] == "date" for f in fields):
            stdlib_imports.append("from datetime import date")

        lines = ["from __future__ import annotations", ""]
        if stdlib_imports:
            lines.extend(sorted(stdlib_imports))
            lines.append("")
        lines.extend(["from pydantic import BaseModel, ConfigDict, Field", "", ""])
        lines.append(f"class {model.name}(BaseModel):")
        if fields:
            for f in fields:
                lines.append(f"    {self._field_line(f)}")
        else:
            lines.append("    pass")
        lines.extend(
            [
                "    model_config = ConfigDict(",
                "        from_attributes=True,",
                "        populate_by_name=True,",
                '        extra="forbid",',
                "    )",
                "",
            ]
        )
        return "\n".join(lines) + "\n"

    def _field_line(self, f: dict[str, Any]) -> str:
        typ = f["python_type"]
        required = bool(f.get("required"))
        default = f.get("default")
        max_length = f.get("max_length")
        if default is not None:
            default_expr = self._literal(default, typ)
        elif required:
            default_expr = "..."
        else:
            default_expr = "None"
            typ = f"{typ} | None"
        kwargs: list[str] = []
        if max_length and typ.startswith("str"):
            kwargs.append(f"max_length={max_length}")
        if required and typ.startswith("str"):
            kwargs.append("min_length=1")
        if self._is_non_negative_field(f) and typ.startswith(("int", "float")):
            kwargs.append("ge=0")
        if kwargs or default_expr == "...":
            return f"{f['name']}: {typ} = Field({default_expr}{', ' if kwargs else ''}{', '.join(kwargs)})"
        return f"{f['name']}: {typ} = {default_expr}"

    def _literal(self, value: str, typ: str) -> str:
        lowered = str(value).lower()
        if typ == "bool":
            return "True" if lowered == "true" else "False"
        if typ in {"int", "float"}:
            return str(value)
        if value in {"null", "None"}:
            return "None"
        return repr(value)

    def _schema_init(self, models: dict[str, Any]) -> str:
        lines = []
        for name in sorted(models):
            module = self._module_name(name)
            lines.append(f"from app.schemas.{module} import {name}")
        if lines:
            lines.append("")
            lines.append("__all__ = [")
            for name in sorted(models):
                lines.append(f"    {name!r},")
            lines.append("]")
        return "\n".join(lines) + "\n"

    def _dataclass_model_file(self, model: Any) -> str:
        fields = model.attributes.get("fields", [])
        imports = {"from __future__ import annotations", "from dataclasses import dataclass"}
        if any(f["python_type"] == "UUID" for f in fields):
            imports.add("from uuid import UUID")
        if any(f["python_type"] == "datetime" for f in fields):
            imports.add("from datetime import datetime")
        if any(f["python_type"] == "date" for f in fields):
            imports.add("from datetime import date")
        lines = ["from __future__ import annotations", ""]
        imports.discard("from __future__ import annotations")
        lines.extend(sorted(imports))
        lines.extend(["", "", "@dataclass(slots=True)", f"class {model.name}Record:"])
        if fields:
            for f in fields:
                lines.append(f"    {f['name']}: {f['python_type']}")
        else:
            lines.append("    pass")
        return "\n".join(lines) + "\n"

    def _sqlalchemy_model_file(self, model: Any) -> str:
        fields = model.attributes.get("fields", [])
        stdlib_imports = ["from uuid import uuid4"]
        if any(f["python_type"] == "datetime" for f in fields):
            stdlib_imports.append("from datetime import datetime")
        if any(f["python_type"] == "date" for f in fields):
            stdlib_imports.append("from datetime import date")

        sqlalchemy_imports = {self._sa_type_name(f) for f in fields}
        lines = ["from __future__ import annotations", ""]
        lines.extend(sorted(stdlib_imports))
        lines.append("")
        if sqlalchemy_imports:
            lines.append(f"from sqlalchemy import {', '.join(sorted(sqlalchemy_imports))}")
        lines.append("from sqlalchemy.orm import Mapped, mapped_column")
        lines.append("")
        lines.append("from app.db.base import Base")
        lines.extend(["", "", f"class {model.name}Record(Base):"])
        lines.append(f"    __tablename__ = {self._table_name(model.name)!r}")
        for f in fields:
            lines.append(f"    {self._sa_field_line(f)}")
        return "\n".join(lines) + "\n"

    def _table_name(self, model_name: str) -> str:
        module = self._module_name(model_name)
        return module if module.endswith("s") else f"{module}s"

    def _sa_type_name(self, f: dict[str, Any]) -> str:
        typ = f["python_type"]
        if typ in {"str", "UUID"}:
            return "String"
        if typ == "int":
            return "Integer"
        if typ == "bool":
            return "Boolean"
        if typ == "float":
            return "Float"
        if typ == "datetime":
            return "DateTime"
        if typ == "date":
            return "Date"
        return "String"

    def _sa_field_line(self, f: dict[str, Any]) -> str:
        py_type = "str" if f["python_type"] == "UUID" else f["python_type"]
        col_type = self._sa_type_name(f)
        if col_type == "String":
            length = f.get("max_length") or (36 if f["python_type"] == "UUID" else 255)
            type_expr = f"String({length})"
        elif col_type == "DateTime":
            type_expr = "DateTime(timezone=True)"
        else:
            type_expr = f"{col_type}()"
        args = [type_expr]
        if f.get("primary"):
            args.append("primary_key=True")
        if f.get("unique"):
            args.append("unique=True")
            args.append("index=True")
        args.append(f"nullable={not bool(f.get('required') or f.get('primary'))}")
        if f["python_type"] == "UUID" and f.get("primary"):
            args.append("default=lambda: str(uuid4())")
        elif f.get("default") is not None:
            args.append(f"default={self._literal(f['default'], f['python_type'])}")
        if len(", ".join(args)) <= 72:
            return f"{f['name']}: Mapped[{py_type}] = mapped_column({', '.join(args)})"
        formatted_args = ",\n        ".join(args)
        return f"{f['name']}: Mapped[{py_type}] = mapped_column(\n        {formatted_args}\n    )"

    def _repository_file(self, model: Any, repo_strategy: str) -> str:
        if repo_strategy == "sqlalchemy":
            return self._sqlalchemy_repository_file(model)
        return self._in_memory_repository_file(model)

    def _primary_field(self, fields: list[dict[str, Any]]) -> dict[str, Any] | None:
        return next((f for f in fields if f.get("primary")), None)

    def _unique_fields(self, fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [f for f in fields if f.get("unique")]

    def _is_non_negative_field(self, f: dict[str, Any]) -> bool:
        return f["python_type"] in {"int", "float"} and f["name"].lower() in {
            "quantity",
            "count",
            "stock",
            "amount",
            "total",
        }

    def _in_memory_repository_file(self, model: Any) -> str:
        module = self._module_name(model.name)
        fields = model.attributes.get("fields", [])
        primary = self._primary_field(fields)
        id_field = primary["name"] if primary else "id"
        unique_fields = self._unique_fields(fields)
        create_name = f"{model.name}Create"
        lines = [
            "from __future__ import annotations",
            "",
            "from threading import RLock",
            "from uuid import uuid4",
            "",
            "from app.core.errors import DuplicateResourceError, NotFoundError",
            f"from app.schemas.{module} import {model.name}",
            f"from app.schemas.{self._module_name(create_name)} import {create_name}",
            "",
            "",
            f"class {model.name}Repository:",
            "    def __init__(self) -> None:",
            f"        self._items: dict[str, {model.name}] = {{}}",
            "        self._lock = RLock()",
            "",
            f"    def list(self, *, offset: int = 0, limit: int = 100) -> list[{model.name}]:",
            "        with self._lock:",
            "            return list(self._items.values())[offset : offset + limit]",
            "",
            f"    def create(self, payload: {create_name}) -> {model.name}:",
            '        data = payload.model_dump(mode="json")',
            "        with self._lock:",
        ]
        if unique_fields:
            lines.append("            self._raise_on_unique_conflict(data)")
        lines.extend(
            [
                f"            item_id = str(data.get({id_field!r}) or uuid4())",
                f"            data[{id_field!r}] = item_id",
                f"            item = {model.name}(**data)",
                "            self._items[item_id] = item",
                "            return item",
                "",
                f"    def get(self, item_id: str) -> {model.name}:",
                "        with self._lock:",
                "            try:",
                "                return self._items[item_id]",
                "            except KeyError as exc:",
                "                raise NotFoundError(item_id) from exc",
                "",
                f"    def update(self, item_id: str, payload: {create_name}) -> {model.name}:",
                '        data = payload.model_dump(mode="json")',
                "        with self._lock:",
                "            current = self.get(item_id)",
            ]
        )
        if unique_fields:
            lines.append("            self._raise_on_unique_conflict(data, ignore_id=item_id)")
        lines.extend(
            [
                "            merged = current.model_dump()",
                "            merged.update(data)",
                f"            merged[{id_field!r}] = item_id",
                f"            item = {model.name}(**merged)",
                "            self._items[item_id] = item",
                "            return item",
                "",
                f"    def delete(self, item_id: str) -> {model.name}:",
                "        with self._lock:",
                "            item = self.get(item_id)",
                "            del self._items[item_id]",
                "            return item",
            ]
        )
        if unique_fields:
            lines.extend(
                [
                    "",
                    "    def _raise_on_unique_conflict(",
                    "        self,",
                    "        data: dict[str, object],",
                    "        *,",
                    "        ignore_id: str | None = None,",
                    "    ) -> None:",
                    "        for existing_id, existing in self._items.items():",
                    "            if ignore_id is not None and existing_id == ignore_id:",
                    "                continue",
                ]
            )
            for field in unique_fields:
                lines.extend(
                    [
                        f"            if existing.{field['name']} == data.get({field['name']!r}):",
                        f"                raise DuplicateResourceError({field['name']!r}, str(data.get({field['name']!r})))",
                    ]
                )
        return "\n".join(lines) + "\n"

    def _sqlalchemy_repository_file(self, model: Any) -> str:
        module = self._module_name(model.name)
        create_name = f"{model.name}Create"
        lines = [
            "from __future__ import annotations",
            "",
            "from sqlalchemy import select",
            "from sqlalchemy.exc import IntegrityError",
            "from sqlalchemy.orm import Session",
            "",
            "from app.core.errors import DuplicateResourceError, NotFoundError",
            f"from app.models.{module} import {model.name}Record",
            f"from app.schemas.{self._module_name(create_name)} import {create_name}",
            "",
            "",
            f"class {model.name}Repository:",
            f"    def list(self, db: Session, *, offset: int = 0, limit: int = 100) -> list[{model.name}Record]:",
            f"        stmt = select({model.name}Record).offset(offset).limit(limit)",
            "        return list(db.execute(stmt).scalars().all())",
            "",
            f"    def get(self, db: Session, item_id: str) -> {model.name}Record:",
            f"        row = db.get({model.name}Record, item_id)",
            "        if row is None:",
            "            raise NotFoundError(item_id)",
            "        return row",
        ]
        for field in self._unique_fields(model.attributes.get("fields", [])):
            lines.extend(
                [
                    "",
                    f"    def get_by_{field['name']}(self, db: Session, value: str) -> {model.name}Record | None:",
                    f"        stmt = select({model.name}Record).where({model.name}Record.{field['name']} == value).limit(1)",
                    "        return db.execute(stmt).scalar_one_or_none()",
                ]
            )
        lines.extend(
            [
                "",
                f"    def create(self, db: Session, payload: {create_name}) -> {model.name}Record:",
                f'        row = {model.name}Record(**payload.model_dump(mode="json"))',
                "        db.add(row)",
                "        try:",
                "            db.flush()",
                "        except IntegrityError as exc:",
                "            db.rollback()",
                '            raise DuplicateResourceError("unique", "conflict") from exc',
                "        return row",
                "",
                f"    def update(self, db: Session, item_id: str, payload: {create_name}) -> {model.name}Record:",
                "        row = self.get(db, item_id)",
                '        for field, value in payload.model_dump(mode="json").items():',
                "            setattr(row, field, value)",
                "        try:",
                "            db.flush()",
                "        except IntegrityError as exc:",
                "            db.rollback()",
                '            raise DuplicateResourceError("unique", "conflict") from exc',
                "        return row",
                "",
                f"    def delete(self, db: Session, item_id: str) -> {model.name}Record:",
                "        row = self.get(db, item_id)",
                "        db.delete(row)",
                "        db.flush()",
                "        return row",
            ]
        )
        return "\n".join(lines) + "\n"

    def _service_file(self, model: Any, repo_strategy: str) -> str:
        module = self._module_name(model.name)
        create_name = f"{model.name}Create"
        fields = model.attributes.get("fields", [])
        validation_lines = self._domain_validation_lines(fields, "payload")
        unique_fields = self._unique_fields(fields)
        if repo_strategy == "sqlalchemy":
            unique_prechecks: list[str] = []
            for field in unique_fields:
                unique_prechecks.extend(
                    [
                        f"existing_{field['name']} = self.repository.get_by_{field['name']}(db, payload.{field['name']})",
                        f"if existing_{field['name']} is not None:",
                        f"    raise DuplicateResourceError({field['name']!r}, str(payload.{field['name']}))",
                    ]
                )
            if not unique_prechecks:
                unique_prechecks.append("pass")
            return dedent(f"""
                from __future__ import annotations

                from sqlalchemy.orm import Session

                from app.core.errors import DuplicateResourceError, ValidationDomainError
                from app.repositories.{module}_repository import {model.name}Repository
                from app.schemas.{module} import {model.name}
                from app.schemas.{self._module_name(create_name)} import {create_name}


                class {model.name}Service:
                    def __init__(self, repository: {model.name}Repository) -> None:
                        self.repository = repository

                    def list(self, db: Session, *, offset: int = 0, limit: int = 100) -> list[{model.name}]:
                        rows = self.repository.list(db, offset=offset, limit=limit)
                        return [{model.name}.model_validate(row) for row in rows]

                    def create(self, payload: {create_name}, db: Session) -> {model.name}:
{self._indent_lines(validation_lines, 24)}
{self._indent_lines(unique_prechecks, 24)}
                        row = self.repository.create(db, payload)
                        db.commit()
                        db.refresh(row)
                        return {model.name}.model_validate(row)

                    def get(self, item_id: str, db: Session) -> {model.name}:
                        row = self.repository.get(db, item_id)
                        return {model.name}.model_validate(row)

                    def update(self, item_id: str, payload: {create_name}, db: Session) -> {model.name}:
{self._indent_lines(validation_lines, 24)}
                        row = self.repository.update(db, item_id, payload)
                        db.commit()
                        db.refresh(row)
                        return {model.name}.model_validate(row)

                    def delete(self, item_id: str, db: Session) -> {model.name}:
                        row = self.repository.delete(db, item_id)
                        result = {model.name}.model_validate(row)
                        db.commit()
                        return result


                repository = {model.name}Repository()
                service = {model.name}Service(repository)
            """).lstrip()
        return dedent(f"""
            from __future__ import annotations

            from app.core.errors import ValidationDomainError
            from app.repositories.{module}_repository import {model.name}Repository
            from app.schemas.{module} import {model.name}
            from app.schemas.{self._module_name(create_name)} import {create_name}


            class {model.name}Service:
                def __init__(self, repository: {model.name}Repository) -> None:
                    self.repository = repository

                def list(self, *, offset: int = 0, limit: int = 100) -> list[{model.name}]:
                    return self.repository.list(offset=offset, limit=limit)

                def create(self, payload: {create_name}) -> {model.name}:
{self._indent_lines(validation_lines, 20)}
                    return self.repository.create(payload)

                def get(self, item_id: str) -> {model.name}:
                    return self.repository.get(item_id)

                def update(self, item_id: str, payload: {create_name}) -> {model.name}:
{self._indent_lines(validation_lines, 20)}
                    return self.repository.update(item_id, payload)

                def delete(self, item_id: str) -> {model.name}:
                    return self.repository.delete(item_id)


            repository = {model.name}Repository()
            service = {model.name}Service(repository)
        """).lstrip()

    def _domain_validation_lines(
        self, fields: list[dict[str, Any]], payload_name: str
    ) -> list[str]:
        lines: list[str] = []
        for f in fields:
            if self._is_non_negative_field(f):
                lines.extend(
                    [
                        f"if {payload_name}.{f['name']} is not None and {payload_name}.{f['name']} < 0:",
                        f"    raise ValidationDomainError({f['name']!r}, 'must be non-negative')",
                    ]
                )
        if not lines:
            lines.append("pass")
        return lines

    def _routes_file(self, model: Any, routes: list[RoutePlan], repo_strategy: str) -> str:
        module = self._module_name(model.name)
        create_names = sorted({r.body for r in routes if r.body and r.body != model.name})

        lines = [
            "from __future__ import annotations",
            "",
            "from typing import Annotated",
            "",
            "from fastapi import APIRouter, Depends, Query, status",
        ]
        if repo_strategy == "sqlalchemy":
            lines.append("from sqlalchemy.orm import Session")
        lines.extend(
            [
                "",
                "from app.core.security import TokenClaims, get_current_user",
            ]
        )
        if repo_strategy == "sqlalchemy":
            lines.append("from app.db.session import get_db")
        lines.append(f"from app.schemas.{module} import {model.name}")
        for cname in create_names:
            lines.append(f"from app.schemas.{self._module_name(cname)} import {cname}")
        lines.append(f"from app.services.{module}_service import service")
        lines.extend(["", f"router = APIRouter(tags={[model.name]!r})"])
        lines.extend(
            [
                "LimitQuery = Annotated[int, Query(ge=1, le=500)]",
                "OffsetQuery = Annotated[int, Query(ge=0)]",
            ]
        )
        if repo_strategy == "sqlalchemy":
            lines.append("DbSession = Annotated[Session, Depends(get_db)]")
        if any(r.auth_required for r in routes):
            lines.append("CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]")
        lines.append("")

        for r in sorted(routes, key=lambda x: (x.path, x.method, x.name)):
            response = (
                f"list[{r.returns}]"
                if r.returns and r.returns_list
                else (r.returns or "dict[str, str]")
            )
            decorator = r.method.lower()
            if r.method == "POST":
                lines.append(
                    f"@router.{decorator}("
                    f"{r.path!r}, response_model={response}, status_code=status.HTTP_201_CREATED"
                    ")"
                )
            else:
                lines.append(f"@router.{decorator}({r.path!r}, response_model={response})")
            fn_name = self._module_name(r.name)
            params: list[str] = []
            path_params = self._path_params(r.path)
            params.extend(f"{name}: str" for name in path_params)
            if r.body:
                params.append(f"payload: {r.body}")
            if repo_strategy == "sqlalchemy":
                params.append("db: DbSession")
            if r.auth_required:
                params.append("_current_user: CurrentUser")
            if r.method == "GET" and r.returns_list:
                params.append("limit: LimitQuery = 100")
                params.append("offset: OffsetQuery = 0")
            lines.append(f"def {fn_name}(")
            for param in params:
                lines.append(f"    {param},")
            lines.append(f") -> {response}:")
            if r.auth_required:
                lines.append("    _ = _current_user")
            item_id_expr = path_params[0] if path_params else "''"
            if r.method == "GET" and r.returns_list:
                if repo_strategy == "sqlalchemy":
                    lines.append("    return service.list(db, offset=offset, limit=limit)")
                else:
                    lines.append("    return service.list(offset=offset, limit=limit)")
            elif r.method == "GET" and path_params:
                if repo_strategy == "sqlalchemy":
                    lines.append(f"    return service.get({item_id_expr}, db)")
                else:
                    lines.append(f"    return service.get({item_id_expr})")
            elif r.method == "POST" and r.body:
                if repo_strategy == "sqlalchemy":
                    lines.append("    return service.create(payload, db)")
                else:
                    lines.append("    return service.create(payload)")
            elif r.method in {"PATCH", "PUT"} and r.body and path_params:
                if repo_strategy == "sqlalchemy":
                    lines.append(f"    return service.update({item_id_expr}, payload, db)")
                else:
                    lines.append(f"    return service.update({item_id_expr}, payload)")
            elif r.method == "DELETE" and path_params:
                if repo_strategy == "sqlalchemy":
                    lines.append(f"    return service.delete({item_id_expr}, db)")
                else:
                    lines.append(f"    return service.delete({item_id_expr})")
            else:
                lines.append("    return {'detail': 'Route declared but no generator exists yet.'}")
            lines.append("")
        return "\n".join(lines) + "\n"

    def _path_params(self, path: str) -> list[str]:
        return re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", path)

    def _main(self, routes: list[RoutePlan], repo_strategy: str, project_name: str) -> str:
        modules = sorted({self._module_name(r.entity) for r in routes})
        modules.append("platform")
        lines = [
            "from __future__ import annotations",
            "",
            "from collections.abc import AsyncIterator",
            "from contextlib import asynccontextmanager",
            "",
            "from fastapi import FastAPI, Request, status",
            "from fastapi.responses import JSONResponse",
            "",
        ]
        for module in modules:
            lines.append(f"from app.api.routes import {module}")
        lines.extend(
            [
                "from app.core.config import get_settings",
                "from app.core.errors import (",
                "    DomainError,",
                "    DuplicateResourceError,",
                "    NotFoundError,",
                "    ValidationDomainError,",
                ")",
                "from app.core.logging import configure_logging",
            ]
        )
        if repo_strategy == "sqlalchemy":
            lines.append("from app.db.session import check_database_connection, create_schema")
        lines.append("from app.middleware.request_id import RequestIDMiddleware, get_request_id")
        lines.extend(
            [
                "",
                "settings = get_settings()",
                "configure_logging(settings.log_level)",
                "",
                "",
                "@asynccontextmanager",
                "async def lifespan(app: FastAPI) -> AsyncIterator[None]:",
            ]
        )
        if repo_strategy == "sqlalchemy":
            lines.append("    if settings.create_db_on_startup:")
            lines.append("        create_schema()")
        else:
            lines.append("    _ = app")
        lines.extend(
            [
                "    yield",
                "",
                "",
                "app = FastAPI(",
                "    title=settings.app_name,",
                "    version=settings.app_version,",
                "    lifespan=lifespan,",
                ")",
                "app.add_middleware(RequestIDMiddleware)",
                "",
            ]
        )
        for module in modules:
            lines.append(f"app.include_router({module}.router)")
        lines.extend(
            [
                "",
                "",
                "def _error_payload(code: str, detail: str) -> dict[str, str]:",
                "    return {'code': code, 'detail': detail, 'request_id': get_request_id()}",
                "",
                "",
                "@app.exception_handler(NotFoundError)",
                "async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:",
                "    _ = request",
                "    return JSONResponse(",
                "        status_code=status.HTTP_404_NOT_FOUND,",
                "        content=_error_payload(exc.code, str(exc)),",
                "    )",
                "",
                "",
                "@app.exception_handler(DuplicateResourceError)",
                "async def duplicate_handler(request: Request, exc: DuplicateResourceError) -> JSONResponse:",
                "    _ = request",
                "    return JSONResponse(",
                "        status_code=status.HTTP_409_CONFLICT,",
                "        content=_error_payload(exc.code, str(exc)),",
                "    )",
                "",
                "",
                "@app.exception_handler(ValidationDomainError)",
                "async def validation_domain_handler(",
                "    request: Request,",
                "    exc: ValidationDomainError,",
                ") -> JSONResponse:",
                "    _ = request",
                "    return JSONResponse(",
                "        status_code=status.HTTP_400_BAD_REQUEST,",
                "        content=_error_payload(exc.code, str(exc)),",
                "    )",
                "",
                "",
                "@app.exception_handler(DomainError)",
                "async def domain_handler(request: Request, exc: DomainError) -> JSONResponse:",
                "    _ = request",
                "    return JSONResponse(",
                "        status_code=status.HTTP_400_BAD_REQUEST,",
                "        content=_error_payload(exc.code, str(exc)),",
                "    )",
                "",
                "",
                "@app.get('/healthz')",
                "def healthz() -> dict[str, str]:",
                "    return {",
                "        'status': 'ok',",
                "        'app': settings.app_name,",
                "        'version': settings.app_version,",
                "        'request_id': get_request_id(),",
                "    }",
                "",
                "",
                "@app.get('/readyz')",
                "def readyz() -> dict[str, str]:",
            ]
        )
        if repo_strategy == "sqlalchemy":
            lines.append("    check_database_connection()")
        lines.extend(
            [
                "    return {",
                "        'status': 'ready',",
                "        'app': settings.app_name,",
                "        'request_id': get_request_id(),",
                "    }",
                "",
            ]
        )
        return "\n".join(lines)

    def _config(self, project_name: str) -> str:
        slug = self._module_name(project_name).replace("_", "-") or "generated-sml-application"
        return dedent(f"""
            from __future__ import annotations

            from functools import lru_cache

            from pydantic import Field
            from pydantic_settings import BaseSettings, SettingsConfigDict


            class Settings(BaseSettings):
                app_name: str = {project_name!r}
                app_slug: str = {slug!r}
                app_version: str = "0.1.0"
                environment: str = "development"
                database_url: str = "sqlite:///./app.db"
                create_db_on_startup: bool = False
                jwt_secret_key: str = Field(default="change-me-in-production-please-rotate", min_length=32)
                jwt_algorithm: str = "HS256"
                jwt_issuer: str = {slug!r}
                jwt_audience: str | None = None
                access_token_expire_minutes: int = 30
                log_level: str = "INFO"

                model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


            @lru_cache
            def get_settings() -> Settings:
                return Settings()
        """).lstrip()

    def _logging(self) -> str:
        return dedent("""
            from __future__ import annotations

            import logging


            def configure_logging(level: str = "INFO") -> None:
                logging.basicConfig(
                    level=getattr(logging, level.upper(), logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s",
                )


            def get_logger(name: str) -> logging.Logger:
                return logging.getLogger(name)
        """).lstrip()

    def _request_id_middleware(self) -> str:
        return dedent("""
            from __future__ import annotations

            from contextvars import ContextVar
            from uuid import uuid4

            from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
            from starlette.requests import Request
            from starlette.responses import Response

            _request_id: ContextVar[str] = ContextVar("request_id", default="-")


            def get_request_id() -> str:
                return _request_id.get()


            class RequestIDMiddleware(BaseHTTPMiddleware):
                async def dispatch(
                    self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                ) -> Response:
                    request_id = request.headers.get("x-request-id", str(uuid4()))
                    token = _request_id.set(request_id)
                    try:
                        response = await call_next(request)
                    finally:
                        _request_id.reset(token)
                    response.headers["x-request-id"] = request_id
                    return response
        """).lstrip()

    def _models_init(self, entity_names: set[str]) -> str:
        lines: list[str] = []
        exported: list[str] = []
        for name in sorted(entity_names):
            module = self._module_name(name)
            record = f"{name}Record"
            lines.append(f"from app.models.{module} import {record}")
            exported.append(record)
        if exported:
            lines.extend(["", "__all__ = ["])
            for record in exported:
                lines.append(f"    {record!r},")
            lines.append("]")
        return "\n".join(lines) + "\n"

    def _db_base(self) -> str:
        return "from sqlalchemy.orm import DeclarativeBase\n\n\nclass Base(DeclarativeBase):\n    pass\n"

    def _db_session(self, entity_names: list[str]) -> str:
        import_lines = [
            f"import app.models.{self._module_name(name)}  # noqa: F401" for name in entity_names
        ]
        lines = [
            "from __future__ import annotations",
            "",
            "from collections.abc import Generator",
            "",
            "from sqlalchemy import create_engine, text",
            "from sqlalchemy.orm import Session, sessionmaker",
            "",
        ]
        if import_lines:
            lines.extend(import_lines)
        lines.extend(
            [
                "from app.core.config import get_settings",
                "from app.db.base import Base",
            ]
        )
        lines.extend(
            [
                "",
                "settings = get_settings()",
                "connect_args = (",
                "    {'check_same_thread': False}",
                "    if settings.database_url.startswith('sqlite')",
                "    else {}",
                ")",
                "engine = create_engine(",
                "    settings.database_url,",
                "    connect_args=connect_args,",
                "    pool_pre_ping=True,",
                ")",
                "SessionLocal = sessionmaker(",
                "    autocommit=False,",
                "    autoflush=False,",
                "    expire_on_commit=False,",
                "    bind=engine,",
                ")",
                "",
                "",
                "def get_db() -> Generator[Session, None, None]:",
                "    db = SessionLocal()",
                "    try:",
                "        yield db",
                "    finally:",
                "        db.close()",
                "",
                "",
                "def create_schema() -> None:",
                "    Base.metadata.create_all(bind=engine)",
                "",
                "",
                "def check_database_connection() -> None:",
                "    with engine.connect() as connection:",
                "        connection.execute(text('SELECT 1'))",
            ]
        )
        return "\n".join(lines) + "\n"

    def _errors(self) -> str:
        return dedent("""
            from __future__ import annotations


            class DomainError(Exception):
                code = "domain_error"


            class NotFoundError(DomainError):
                code = "not_found"

                def __init__(self, item_id: str) -> None:
                    super().__init__(f"Resource not found: {item_id}")


            class DuplicateResourceError(DomainError):
                code = "duplicate_resource"

                def __init__(self, field: str, value: str) -> None:
                    super().__init__(f"Duplicate value for {field}: {value}")


            class ValidationDomainError(DomainError):
                code = "validation_error"

                def __init__(self, field: str, reason: str) -> None:
                    super().__init__(f"Invalid {field}: {reason}")
        """).lstrip()

    def _security(self, enabled: bool) -> str:
        if not enabled:
            return dedent("""
                from __future__ import annotations

                from pydantic import BaseModel, Field


                class TokenClaims(BaseModel):
                    sub: str = "anonymous"
                    scopes: list[str] = Field(default_factory=list)


                def create_access_token(subject: str, scopes: list[str] | None = None) -> str:
                    _ = scopes
                    return subject


                def get_current_user() -> TokenClaims:
                    return TokenClaims()
            """).lstrip()
        return dedent("""
            from __future__ import annotations

            from collections.abc import Callable, Sequence
            from datetime import UTC, datetime, timedelta
            from typing import Annotated, Any, cast

            import jwt
            from fastapi import Depends, HTTPException, status
            from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
            from pydantic import BaseModel, ConfigDict, Field

            from app.core.config import get_settings

            bearer = HTTPBearer(auto_error=False)
            BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


            class TokenClaims(BaseModel):
                sub: str = Field(..., min_length=1)
                scopes: list[str] = Field(default_factory=list)
                iss: str | None = None
                aud: str | None = None
                exp: int | None = None
                model_config = ConfigDict(extra="allow")


            def create_access_token(
                subject: str,
                scopes: Sequence[str] | None = None,
                expires_delta: timedelta | None = None,
            ) -> str:
                settings = get_settings()
                now = datetime.now(UTC)
                expire = now + (
                    expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
                )
                payload: dict[str, object] = {
                    "sub": subject,
                    "scopes": list(scopes or []),
                    "iss": settings.jwt_issuer,
                    "iat": now,
                    "nbf": now,
                    "exp": expire,
                }
                if settings.jwt_audience:
                    payload["aud"] = settings.jwt_audience
                return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


            def decode_access_token(token: str) -> TokenClaims:
                settings = get_settings()
                decode_options = cast(Any, {"verify_aud": bool(settings.jwt_audience)})
                try:
                    payload = jwt.decode(
                        token,
                        settings.jwt_secret_key,
                        algorithms=[settings.jwt_algorithm],
                        issuer=settings.jwt_issuer,
                        audience=settings.jwt_audience,
                        options=decode_options,
                    )
                except jwt.PyJWTError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid bearer token",
                    ) from exc
                return TokenClaims.model_validate(payload)


            def get_current_user(credentials: BearerCredentials) -> TokenClaims:
                if credentials is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Missing bearer token",
                    )
                return decode_access_token(credentials.credentials)


            CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


            def require_scopes(required_scopes: Sequence[str]) -> Callable[[TokenClaims], TokenClaims]:
                def dependency(current_user: CurrentUser) -> TokenClaims:
                    missing = set(required_scopes) - set(current_user.scopes)
                    if missing:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Insufficient token scope",
                        )
                    return current_user

                return dependency
        """).lstrip()

    def _test_files(
        self, graph: SIRGraph, models: dict[str, Any], routes: list[RoutePlan], repo_strategy: str
    ) -> dict[str, str]:
        routes_by_entity: dict[str, list[RoutePlan]] = {}
        for route in routes:
            routes_by_entity.setdefault(route.entity, []).append(route)
        first_get = next((r for r in routes if r.method == "GET"), None)
        first_entity = next(iter(sorted(routes_by_entity)), next(iter(models), "Resource"))
        security_import = "from app.core.security import create_access_token"
        files: dict[str, str] = {}

        if repo_strategy == "sqlalchemy":
            files["tests/conftest.py"] = dedent("""
                from __future__ import annotations

                import os
                from pathlib import Path

                os.environ.setdefault("DATABASE_URL", "sqlite:///./test_app.db")
                os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-change-me-32-bytes-min")
                os.environ.setdefault("CREATE_DB_ON_STARTUP", "false")

                import pytest
                from fastapi.testclient import TestClient

                from app.db.session import Base, engine
                from app.main import app


                @pytest.fixture(autouse=True)
                def reset_database(tmp_path: Path):
                    _ = tmp_path
                    Base.metadata.drop_all(bind=engine)
                    Base.metadata.create_all(bind=engine)
                    yield
                    Base.metadata.drop_all(bind=engine)


                @pytest.fixture
                def client() -> TestClient:
                    return TestClient(app)
            """).lstrip()
        else:
            repository_imports: list[str] = []
            repository_names: list[str] = []
            for entity in sorted(routes_by_entity):
                module = self._module_name(entity)
                variable = f"{module}_repository"
                repository_imports.append(
                    f"from app.services.{module}_service import repository as {variable}"
                )
                repository_names.append(variable)
            repositories_expr = "[" + ", ".join(repository_names) + "]"
            files["tests/conftest.py"] = dedent(f"""
                from __future__ import annotations

                import os

                os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-change-me-32-bytes-min")

                import pytest
                from fastapi.testclient import TestClient

                from app.main import app
                {chr(10).join(repository_imports)}

                _REPOSITORIES = {repositories_expr}


                @pytest.fixture(autouse=True)
                def reset_in_memory_repositories():
                    for repository in _REPOSITORIES:
                        repository._items.clear()
                    yield
                    for repository in _REPOSITORIES:
                        repository._items.clear()


                @pytest.fixture
                def client() -> TestClient:
                    return TestClient(app)
            """).lstrip()

        payloads: dict[str, dict[str, object]] = {}
        payloads_2: dict[str, dict[str, object]] = {}
        invalid_payloads: dict[str, dict[str, object]] = {}
        duplicate_payloads: dict[str, dict[str, object]] = {}
        unique_entities: list[str] = []
        for entity in sorted(routes_by_entity):
            entity_routes = routes_by_entity[entity]
            post_route = next((r for r in entity_routes if r.method == "POST" and r.body), None)
            reference_model = (
                models.get(post_route.body)
                if post_route and post_route.body
                else models.get(entity)
            )
            payloads[entity] = self._sample_payload(reference_model, include_primary=False)
            payloads_2[entity] = self._sample_payload(
                reference_model, include_primary=False, suffix=f"{self._module_name(entity)}-two"
            )
            invalid_payloads[entity] = self._invalid_payload(reference_model)
            duplicate_payloads[entity] = dict(payloads[entity])
            if self._unique_fields(
                reference_model.attributes.get("fields", []) if reference_model else []
            ):
                unique_entities.append(entity)

        payloads_repr = pformat(payloads, width=60)
        payloads_2_repr = pformat(payloads_2, width=60)
        invalid_payloads_repr = pformat(invalid_payloads, width=60)
        duplicate_payloads_repr = pformat(duplicate_payloads, width=60)

        def assignment_lines(name: str, value_repr: str) -> list[str]:
            return [
                f"{name}: dict[str, dict[str, object]] = (",
                *[f"    {line}" for line in value_repr.splitlines()],
                ")",
            ]

        factory_lines = [
            "from __future__ import annotations",
            "",
            security_import,
            "",
            *assignment_lines("PAYLOADS", payloads_repr),
            *assignment_lines("SECOND_PAYLOADS", payloads_2_repr),
            *assignment_lines("INVALID_PAYLOADS", invalid_payloads_repr),
            *assignment_lines("DUPLICATE_PAYLOADS", duplicate_payloads_repr),
            f"DEFAULT_ENTITY = {first_entity!r}",
            "",
            "",
            'def auth_headers(subject: str = "test-user") -> dict[str, str]:',
            '    token = create_access_token(subject=subject, scopes=["user"])',
            '    return {"Authorization": f"Bearer {token}"}',
            "",
            "",
            "def valid_payload(entity: str = DEFAULT_ENTITY) -> dict[str, object]:",
            "    return dict(PAYLOADS[entity])",
            "",
            "",
            "def second_payload(entity: str = DEFAULT_ENTITY) -> dict[str, object]:",
            "    return dict(SECOND_PAYLOADS[entity])",
            "",
            "",
            "def invalid_payload(entity: str = DEFAULT_ENTITY) -> dict[str, object]:",
            "    return dict(INVALID_PAYLOADS[entity])",
            "",
            "",
            "def duplicate_payload(entity: str = DEFAULT_ENTITY) -> dict[str, object]:",
            "    return dict(DUPLICATE_PAYLOADS[entity])",
            "",
        ]
        files["tests/factories.py"] = "\n".join(factory_lines)

        if routes:
            test_lines = [
                "from __future__ import annotations",
                "",
                "from tests.factories import (",
                "    auth_headers,",
                "    duplicate_payload,",
                "    invalid_payload,",
                "    second_payload,",
                "    valid_payload,",
                ")",
                "",
                "",
                "def _path(template: str, item_id: str) -> str:",
                "    return template.replace('{id}', item_id)",
                "",
                "",
                "def test_healthz_returns_request_id(client) -> None:",
                "    response = client.get('/healthz', headers={'x-request-id': 'req-test'})",
                "    assert response.status_code == 200",
                "    assert response.json()['status'] == 'ok'",
                "    assert response.headers['x-request-id'] == 'req-test'",
                "",
                "",
                "def test_readyz_returns_ready(client) -> None:",
                "    response = client.get('/readyz')",
                "    assert response.status_code == 200",
                "    assert response.json()['status'] == 'ready'",
                "",
            ]
            if first_get is not None and first_get.auth_required:
                test_lines.extend(
                    [
                        "",
                        "def test_authentication_is_required(client) -> None:",
                        f"    response = client.get({first_get.path!r})",
                        "    assert response.status_code == 401",
                        "",
                    ]
                )
            for entity in sorted(routes_by_entity):
                entity_routes = routes_by_entity[entity]
                list_route = next(
                    (r for r in entity_routes if r.method == "GET" and r.returns_list), None
                )
                create_route = next(
                    (r for r in entity_routes if r.method == "POST" and r.body), None
                )
                get_route = next(
                    (r for r in entity_routes if r.method == "GET" and "{" in r.path), None
                )
                update_route = next(
                    (r for r in entity_routes if r.method in {"PATCH", "PUT"} and "{" in r.path),
                    None,
                )
                delete_route = next(
                    (r for r in entity_routes if r.method == "DELETE" and "{" in r.path), None
                )
                mod = self._module_name(entity)
                if create_route is None or list_route is None:
                    continue
                test_lines.extend(
                    [
                        "",
                        f"def test_create_and_list_{mod}(client) -> None:",
                        "    response = client.post(",
                        f"        {create_route.path!r},",
                        f"        json=valid_payload({entity!r}),",
                        "        headers=auth_headers(),",
                        "    )",
                        "    assert response.status_code == 201",
                        "    body = response.json()",
                        f"    for key, value in valid_payload({entity!r}).items():",
                        "        assert body[key] == value",
                        "    assert 'id' in body",
                        "",
                        "    response = client.get(",
                        f"        {list_route.path!r},",
                        "        headers=auth_headers(),",
                        "    )",
                        "    assert response.status_code == 200",
                        "    assert len(response.json()) == 1",
                    ]
                )
                if get_route is not None:
                    test_lines.extend(
                        [
                            "",
                            f"def test_get_{mod}_by_id(client) -> None:",
                            "    created = client.post(",
                            f"        {create_route.path!r},",
                            f"        json=valid_payload({entity!r}),",
                            "        headers=auth_headers(),",
                            "    ).json()",
                            f"    response = client.get(_path({get_route.path!r}, created['id']), headers=auth_headers())",
                            "    assert response.status_code == 200",
                            "    assert response.json()['id'] == created['id']",
                        ]
                    )
                if update_route is not None:
                    test_lines.extend(
                        [
                            "",
                            f"def test_update_{mod}(client) -> None:",
                            "    created = client.post(",
                            f"        {create_route.path!r},",
                            f"        json=valid_payload({entity!r}),",
                            "        headers=auth_headers(),",
                            "    ).json()",
                            "    response = client.patch(",
                            f"        _path({update_route.path!r}, created['id']),",
                            f"        json=second_payload({entity!r}),",
                            "        headers=auth_headers(),",
                            "    )",
                            "    assert response.status_code == 200",
                            f"    for key, value in second_payload({entity!r}).items():",
                            "        assert response.json()[key] == value",
                        ]
                    )
                if delete_route is not None and get_route is not None:
                    test_lines.extend(
                        [
                            "",
                            f"def test_delete_{mod}(client) -> None:",
                            "    created = client.post(",
                            f"        {create_route.path!r},",
                            f"        json=valid_payload({entity!r}),",
                            "        headers=auth_headers(),",
                            "    ).json()",
                            f"    response = client.delete(_path({delete_route.path!r}, created['id']), headers=auth_headers())",
                            "    assert response.status_code == 200",
                            "    assert response.json()['id'] == created['id']",
                            f"    missing = client.get(_path({get_route.path!r}, created['id']), headers=auth_headers())",
                            "    assert missing.status_code == 404",
                        ]
                    )
                if entity in unique_entities:
                    test_lines.extend(
                        [
                            "",
                            f"def test_duplicate_unique_value_is_rejected_for_{mod}(client) -> None:",
                            f"    client.post({create_route.path!r}, json=valid_payload({entity!r}), headers=auth_headers())",
                            "    response = client.post(",
                            f"        {create_route.path!r},",
                            f"        json=duplicate_payload({entity!r}),",
                            "        headers=auth_headers(),",
                            "    )",
                            "    assert response.status_code == 409",
                            "    assert response.json()['code'] == 'duplicate_resource'",
                        ]
                    )
                test_lines.extend(
                    [
                        "",
                        f"def test_domain_validation_rejects_invalid_payload_for_{mod}(client) -> None:",
                        "    response = client.post(",
                        f"        {create_route.path!r},",
                        f"        json=invalid_payload({entity!r}),",
                        "        headers=auth_headers(),",
                        "    )",
                        "    assert response.status_code in {400, 422}",
                    ]
                )
            files["tests/test_api.py"] = "\n".join(test_lines) + "\n"
            service_contract = self._service_contract_test_file(routes_by_entity, repo_strategy)
            if service_contract:
                files["tests/test_service_contracts.py"] = service_contract
        else:
            files["tests/test_api.py"] = dedent("""
                from __future__ import annotations


                def test_healthz_returns_ok(client) -> None:
                    response = client.get("/healthz")
                    assert response.status_code == 200
                    assert response.json()["status"] == "ok"
            """).lstrip()
        files["tests/test_openapi_contract.py"] = self._openapi_contract_test_file(
            models,
            routes,
        )
        files["tests/test_load_smoke.py"] = self._load_smoke_test_file(
            first_get.path if first_get else "/healthz",
            any(r.auth_required for r in routes),
        )
        if repo_strategy == "sqlalchemy":
            files["tests/test_postgres_integration.py"] = self._postgres_integration_test_file()
        files.update(platform_test_files(graph))
        return files

    def _service_contract_test_file(
        self,
        routes_by_entity: dict[str, list[RoutePlan]],
        repo_strategy: str,
    ) -> str:
        entities: list[tuple[str, str]] = []
        for entity in sorted(routes_by_entity):
            create_route = next(
                (
                    route
                    for route in routes_by_entity[entity]
                    if route.method == "POST" and route.body
                ),
                None,
            )
            if create_route is None or create_route.body is None:
                continue
            entities.append((entity, create_route.body))

        if not entities:
            return ""

        imports = [
            "from __future__ import annotations",
            "",
            "from app.core.errors import NotFoundError",
        ]
        if repo_strategy == "sqlalchemy":
            imports.append("from app.db.session import SessionLocal")
        for entity, create_schema in entities:
            module = self._module_name(entity)
            create_module = self._module_name(create_schema)
            service_alias = f"{module}_service"
            imports.append(f"from app.schemas.{create_module} import {create_schema}")
            imports.append(f"from app.services.{module}_service import service as {service_alias}")
        imports.extend(
            [
                "from tests.factories import second_payload, valid_payload",
                "",
                "",
            ]
        )

        lines = imports
        for entity, create_schema in entities:
            module = self._module_name(entity)
            service_alias = f"{module}_service"
            test_name = f"test_{module}_service_full_crud_contract"
            if repo_strategy == "sqlalchemy":
                lines.extend(
                    [
                        f"def {test_name}() -> None:",
                        "    db = SessionLocal()",
                        "    try:",
                        f"        created = {service_alias}.create(",
                        f"            {create_schema}(**valid_payload({entity!r})),",
                        "            db,",
                        "        )",
                        f"        listed = {service_alias}.list(db)",
                        "        assert [item.id for item in listed] == [created.id]",
                        "        item_id = str(created.id)",
                        f"        fetched = {service_alias}.get(item_id, db)",
                        "        assert fetched.id == created.id",
                        f"        updated = {service_alias}.update(",
                        "            item_id,",
                        f"            {create_schema}(**second_payload({entity!r})),",
                        "            db,",
                        "        )",
                        f"        for field, value in second_payload({entity!r}).items():",
                        "            assert str(getattr(updated, field)) == str(value)",
                        f"        deleted = {service_alias}.delete(item_id, db)",
                        "        assert deleted.id == created.id",
                        "        try:",
                        f"            {service_alias}.get(item_id, db)",
                        "        except NotFoundError:",
                        "            pass",
                        "        else:",
                        "            raise AssertionError('expected deleted entity to be missing')",
                        "    finally:",
                        "        db.close()",
                        "",
                        "",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"def {test_name}() -> None:",
                        f"    created = {service_alias}.create(",
                        f"        {create_schema}(**valid_payload({entity!r})),",
                        "    )",
                        f"    listed = {service_alias}.list()",
                        "    assert [item.id for item in listed] == [created.id]",
                        "    item_id = str(created.id)",
                        f"    fetched = {service_alias}.get(item_id)",
                        "    assert fetched.id == created.id",
                        f"    updated = {service_alias}.update(",
                        "        item_id,",
                        f"        {create_schema}(**second_payload({entity!r})),",
                        "    )",
                        f"    for field, value in second_payload({entity!r}).items():",
                        "        assert str(getattr(updated, field)) == str(value)",
                        f"    deleted = {service_alias}.delete(item_id)",
                        "    assert deleted.id == created.id",
                        "    try:",
                        f"        {service_alias}.get(item_id)",
                        "    except NotFoundError:",
                        "        pass",
                        "    else:",
                        "        raise AssertionError('expected deleted entity to be missing')",
                        "",
                        "",
                    ]
                )
        return "\n".join(lines).rstrip() + "\n"

    def _openapi_contract_test_file(
        self,
        models: dict[str, Any],
        routes: list[RoutePlan],
    ) -> str:
        expected_schemas = pformat(sorted(models), width=88)
        expected_routes = pformat(
            [
                {"path": r.path, "method": r.method.lower(), "auth": r.auth_required}
                for r in sorted(routes, key=lambda x: (x.path, x.method, x.name))
            ],
            width=88,
        )
        requires_auth = any(r.auth_required for r in routes)
        lines = [
            "from __future__ import annotations",
            "",
            f"EXPECTED_SCHEMAS = {expected_schemas}",
            f"EXPECTED_ROUTES = {expected_routes}",
            f"REQUIRES_AUTH = {requires_auth!r}",
            "",
            "",
            "def test_openapi_contract_declares_expected_paths_methods_and_schemas(client) -> None:",
            "    response = client.get('/openapi.json')",
            "    assert response.status_code == 200",
            "    spec = response.json()",
            "    assert spec['openapi'].startswith('3.')",
            "    assert spec['info']['title']",
            "",
            "    for route in EXPECTED_ROUTES:",
            "        assert route['path'] in spec['paths']",
            "        assert route['method'] in spec['paths'][route['path']]",
            "        operation = spec['paths'][route['path']][route['method']]",
            "        if route['auth']:",
            "            assert operation['security'] == [{'HTTPBearer': []}]",
            "",
            "    schemas = spec['components']['schemas']",
            "    for schema in EXPECTED_SCHEMAS:",
            "        assert schema in schemas",
            "        assert schemas[schema]['additionalProperties'] is False",
            "",
            "    if REQUIRES_AUTH:",
            "        security_schemes = spec['components']['securitySchemes']",
            "        assert security_schemes['HTTPBearer']['scheme'] == 'bearer'",
        ]
        return "\n".join(lines) + "\n"

    def _load_smoke_test_file(self, list_path: str, requires_auth: bool) -> str:
        auth_import = "from tests.factories import auth_headers" if requires_auth else ""
        headers_expr = "auth_headers()" if requires_auth else "{}"
        return dedent(f"""
            from __future__ import annotations

            {auth_import}


            def test_load_smoke_exercises_health_and_list_hot_paths(client) -> None:
                headers = {headers_expr}
                for index in range(25):
                    response = client.get("/healthz", headers={{"x-request-id": f"load-{{index}}"}})
                    assert response.status_code == 200
                    assert response.headers["x-request-id"] == f"load-{{index}}"

                for _ in range(25):
                    response = client.get({list_path!r}, headers=headers)
                    assert response.status_code in {{200, 401}}
                    if headers:
                        assert response.status_code == 200
        """).lstrip()

    def _postgres_integration_test_file(self) -> str:
        return dedent("""
            from __future__ import annotations

            import os

            import pytest
            from sqlalchemy import text

            from app.core.config import get_settings
            from app.db.session import engine

            pytestmark = pytest.mark.skipif(
                os.environ.get("RUN_POSTGRES_INTEGRATION") != "1",
                reason="set RUN_POSTGRES_INTEGRATION=1 with a PostgreSQL DATABASE_URL to run",
            )


            def test_postgres_database_is_reachable_and_selected() -> None:
                settings = get_settings()
                assert settings.database_url.startswith("postgresql")
                with engine.connect() as connection:
                    assert connection.execute(text("select 1")).scalar_one() == 1
        """).lstrip()

    def _sample_payload(
        self, model: Any | None, *, include_primary: bool, suffix: str = "demo"
    ) -> dict[str, object]:
        payload: dict[str, object] = {}
        if model is None:
            return {"name": suffix}
        for f in model.attributes.get("fields", []):
            if f.get("primary") and not include_primary:
                continue
            name = f["name"]
            typ = f["python_type"]
            if typ == "str":
                payload[name] = (
                    f"{name}-{suffix}" if name.lower() not in {"name", "title"} else suffix
                )
            elif typ == "UUID":
                payload[name] = "00000000-0000-4000-8000-000000000001"
            elif typ == "int":
                payload[name] = 5 if suffix == "demo" else 7
            elif typ == "float":
                payload[name] = 5.0 if suffix == "demo" else 7.0
            elif typ == "bool":
                payload[name] = False
            else:
                payload[name] = suffix
        return payload or {"name": suffix}

    def _invalid_payload(self, model: Any | None) -> dict[str, object]:
        payload = self._sample_payload(model, include_primary=False)
        if model is not None:
            for f in model.attributes.get("fields", []):
                if self._is_non_negative_field(f):
                    payload[f["name"]] = -1
                    return payload
                if f["python_type"] == "str" and f.get("required"):
                    payload[f["name"]] = ""
                    return payload
        payload.pop(next(iter(payload)), None)
        return payload

    def _pyproject(self, resolution: ResolutionResult, repo_strategy: str) -> str:
        deps = [
            "fastapi>=0.110",
            "uvicorn[standard]>=0.27",
            "pydantic>=2.8",
            "pydantic-settings>=2.4",
            "PyJWT>=2.8",
        ]
        if repo_strategy == "sqlalchemy" or any(
            str(f) == "Requires(Dependency:SQLAlchemy)" for f in resolution.facts
        ):
            deps.extend(["sqlalchemy>=2.0", "alembic>=1.13", "psycopg[binary]>=3.1"])

        lines = [
            "[build-system]",
            'requires = ["setuptools>=68", "wheel"]',
            'build-backend = "setuptools.build_meta"',
            "",
            "[project]",
            'name = "generated-sml-app"',
            'version = "0.1.0"',
            'requires-python = ">=3.11"',
            "dependencies = [",
        ]
        lines.extend(f'  "{dependency}",' for dependency in deps)
        lines.extend(
            [
                "]",
                "",
                "[tool.setuptools.packages.find]",
                'include = ["app*"]',
                'exclude = ["tests*", "load*"]',
                "",
                "[project.optional-dependencies]",
                "dev = [",
                '  "pytest>=8",',
                '  "httpx>=0.27",',
                '  "ruff>=0.6",',
                '  "mypy>=1.10",',
                '  "pytest-cov>=5",',
                '  "pip-audit>=2.7",',
                '  "bandit>=1.7",',
                "]",
                "load = [",
                '  "locust>=2.31",',
                "]",
                "",
                "[tool.pytest.ini_options]",
                'pythonpath = ["."]',
                'testpaths = ["tests"]',
                'addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80"',
                'filterwarnings = ["ignore:Using `httpx` with `starlette.testclient` is deprecated:DeprecationWarning"]',
                "",
                "[tool.coverage.run]",
                "branch = true",
                'source = ["app"]',
                "omit = [",
                '  "app/db/migrations/*",',
                '  "app/models/__init__.py",',
                '  "app/schemas/__init__.py",',
                "]",
                "",
                "[tool.coverage.report]",
                "fail_under = 80",
                "show_missing = true",
                "skip_covered = true",
                "",
                "[tool.ruff]",
                "line-length = 100",
                'target-version = "py311"',
                "",
                "[tool.ruff.lint]",
                'select = ["E", "F", "I", "B", "UP", "SIM"]',
                "",
                "[tool.mypy]",
                'python_version = "3.11"',
                'plugins = ["pydantic.mypy"]',
                "warn_unused_configs = true",
                "warn_return_any = true",
                "warn_unused_ignores = true",
                "disallow_untyped_defs = false",
                "ignore_missing_imports = true",
                "",
                "[tool.bandit]",
                'exclude_dirs = ["tests"]',
                "",
            ]
        )
        return "\n".join(lines)

    def _env_example(self, resolution: ResolutionResult, project_name: str) -> str:
        lines = [
            f"APP_NAME={project_name}",
            "ENVIRONMENT=development",
            "JWT_SECRET_KEY=change-me-in-production-please-rotate",
            "JWT_ISSUER=generated-sml-app",
            "JWT_AUDIENCE=",
            "LOG_LEVEL=INFO",
            "CREATE_DB_ON_STARTUP=false",
        ]
        if any(str(f) == "Requires(EnvVar:DATABASE_URL)" for f in resolution.facts):
            lines.extend(
                [
                    "DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app",
                    "POSTGRES_TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app",
                    "RUN_POSTGRES_INTEGRATION=0",
                ]
            )
        else:
            lines.append("DATABASE_URL=sqlite:///./app.db")
        return "\n".join(lines) + "\n"

    def _gitignore(self) -> str:
        return dedent("""
            __pycache__/
            *.py[cod]
            .pytest_cache/
            .ruff_cache/
            .mypy_cache/
            .venv/
            .env
            *.db
            htmlcov/
            .coverage
            coverage.xml
            .locust/
        """).lstrip()

    def _dockerfile(self) -> str:
        return dedent("""
            FROM python:3.12-slim AS runtime

            ENV PYTHONDONTWRITEBYTECODE=1 \
                PYTHONUNBUFFERED=1

            WORKDIR /app
            COPY pyproject.toml ./
            RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .
            COPY . .
            EXPOSE 8000
            CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
        """).lstrip()

    def _dockerignore(self) -> str:
        return dedent("""
            .git/
            .github/
            .mypy_cache/
            .pytest_cache/
            .ruff_cache/
            .venv/
            venv/
            __pycache__/
            *.py[cod]
            *.db
            .coverage
            htmlcov/
        """).lstrip()

    def _docker_compose(self, repo_strategy: str) -> str:
        if repo_strategy != "sqlalchemy":
            return dedent("""
                services:
                  api:
                    build: .
                    ports:
                      - "8000:8000"
                    environment:
                      ENVIRONMENT: development
                      JWT_SECRET_KEY: compose-secret-key-change-me-32-bytes
                      CREATE_DB_ON_STARTUP: "true"
            """).lstrip()
        return dedent("""
            services:
              db:
                image: postgres:16
                environment:
                  POSTGRES_DB: app
                  POSTGRES_USER: app
                  POSTGRES_PASSWORD: app
                ports:
                  - "5432:5432"
                healthcheck:
                  test: ["CMD-SHELL", "pg_isready -U app -d app"]
                  interval: 5s
                  timeout: 5s
                  retries: 20
                volumes:
                  - postgres-data:/var/lib/postgresql/data

              api:
                build: .
                depends_on:
                  db:
                    condition: service_healthy
                ports:
                  - "8000:8000"
                environment:
                  ENVIRONMENT: development
                  DATABASE_URL: postgresql+psycopg://app:app@db:5432/app
                  JWT_SECRET_KEY: compose-secret-key-change-me-32-bytes
                  CREATE_DB_ON_STARTUP: "false"
                command: >
                  sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"

            volumes:
              postgres-data:
        """).lstrip()

    def _locustfile(self, routes: list[RoutePlan]) -> str:
        list_routes = [r for r in routes if r.method == "GET"]
        list_path = list_routes[0].path if list_routes else "/healthz"
        return dedent(f"""
            from __future__ import annotations

            from locust import HttpUser, between, task

            from app.core.security import create_access_token


            class ApiUser(HttpUser):
                wait_time = between(0.05, 0.2)

                def on_start(self) -> None:
                    token = create_access_token(subject="load-user", scopes=["user"])
                    self.headers = {{"Authorization": f"Bearer {{token}}"}}

                @task(3)
                def health(self) -> None:
                    self.client.get("/healthz", name="GET /healthz")

                @task(2)
                def list_resources(self) -> None:
                    self.client.get({list_path!r}, headers=self.headers, name="GET list")
        """).lstrip()

    def _makefile(self, repo_strategy: str) -> str:
        migrate_target = (
            "alembic upgrade head"
            if repo_strategy == "sqlalchemy"
            else "@echo 'No Alembic migration target for this repository strategy'"
        )
        return dedent(f"""
            .PHONY: test lint format-check typecheck security quality run migrate coverage contract load-smoke load-test compose-up compose-down postgres-test

            test:
            \tpytest

            lint:
            \truff check .

            format-check:
            \truff format --check .

            typecheck:
            \tmypy app

            security:
            \tpip-audit
            \tbandit -q -r app

            coverage:
            \tpytest --cov=app --cov-report=term-missing --cov-fail-under=80

            contract:
            \tpytest tests/test_openapi_contract.py

            load-smoke:
            \tpytest tests/test_load_smoke.py

            load-test:
            \tpython -m pip install -e '.[load]'
            \tlocust -f load/locustfile.py --headless --users 10 --spawn-rate 5 --run-time 30s --host http://127.0.0.1:8000

            quality: lint format-check typecheck test security

            run:
            \tuvicorn app.main:app --reload

            migrate:
            \t{migrate_target}

            compose-up:
            \tdocker compose up --build

            compose-down:
            \tdocker compose down -v

            postgres-test:
            \tRUN_POSTGRES_INTEGRATION=1 POSTGRES_TEST_DATABASE_URL=$${{DATABASE_URL}} pytest tests/test_postgres_integration.py
        """).lstrip()

    def _pre_commit(self) -> str:
        return dedent("""
            repos:
              - repo: https://github.com/astral-sh/ruff-pre-commit
                rev: v0.6.9
                hooks:
                  - id: ruff
                    args: [--fix]
                  - id: ruff-format
        """).lstrip()

    def _ci_workflow(self, repo_strategy: str) -> str:
        if repo_strategy == "sqlalchemy":
            return dedent("""
                name: ci

                on:
                  push:
                  pull_request:

                jobs:
                  test:
                    runs-on: ubuntu-latest
                    services:
                      postgres:
                        image: postgres:16
                        env:
                          POSTGRES_DB: app
                          POSTGRES_USER: app
                          POSTGRES_PASSWORD: app
                        ports:
                          - 5432:5432
                        options: >-
                          --health-cmd "pg_isready -U app -d app"
                          --health-interval 5s
                          --health-timeout 5s
                          --health-retries 20
                    env:
                      DATABASE_URL: postgresql+psycopg://app:app@localhost:5432/app
                      POSTGRES_TEST_DATABASE_URL: postgresql+psycopg://app:app@localhost:5432/app
                      RUN_POSTGRES_INTEGRATION: "1"
                      JWT_SECRET_KEY: ci-secret-key-change-me-32-bytes
                      CREATE_DB_ON_STARTUP: "false"
                    steps:
                      - uses: actions/checkout@v4
                      - uses: actions/setup-python@v5
                        with:
                          python-version: "3.12"
                      - run: python -m pip install --upgrade pip
                      - run: pip install -e '.[dev]'
                      - run: ruff check .
                      - run: ruff format --check .
                      - run: mypy app
                      - run: alembic upgrade head
                      - run: alembic downgrade base
                      - run: alembic upgrade head
                      - run: pytest
                      - run: bandit -q -r app
                      - run: pip-audit
            """).lstrip()
        return dedent("""
            name: ci

            on:
              push:
              pull_request:

            jobs:
              test:
                runs-on: ubuntu-latest
                env:
                  JWT_SECRET_KEY: ci-secret-key-change-me-32-bytes
                steps:
                  - uses: actions/checkout@v4
                  - uses: actions/setup-python@v5
                    with:
                      python-version: "3.12"
                  - run: python -m pip install --upgrade pip
                  - run: pip install -e '.[dev]'
                  - run: ruff check .
                  - run: ruff format --check .
                  - run: mypy app
                  - run: pytest
                  - run: bandit -q -r app
                  - run: pip-audit
        """).lstrip()

    def _readme(self, graph: SIRGraph, repo_strategy: str) -> str:
        project = next((n for n in graph.by_type("Project")), None)
        name = project.name if project else "Generated SML Application"
        db_note = (
            "This build uses SQLAlchemy with request-scoped session injection, Alembic migrations, and a PostgreSQL docker-compose profile."
            if repo_strategy == "sqlalchemy"
            else "This build uses an in-memory repository target for local/compiler validation."
        )
        return dedent(f"""
            # {name}

            Generated by Semantic Software Markup Compiler.

            {db_note}

            ## Production-oriented features

            - Layered route/service/repository design.
            - Pydantic settings via environment variables.
            - JWT bearer-token validation with PyJWT.
            - Request IDs and structured error payloads.
            - Centralized domain exception handlers.
            - Deterministic tests using real FastAPI/TestClient behavior.
            - OpenAPI contract tests and coverage thresholds.
            - SQLite smoke tests plus PostgreSQL integration path for SQLAlchemy builds.
            - Ruff, mypy, pytest, Bandit, pip-audit, Docker, CI, and pre-commit scaffolding.
            - Optional Locust load-test scaffold and deterministic load-smoke test.

            ## Run locally

            ```bash
            pip install -e '.[dev]'
            cp .env.example .env
            make migrate
            uvicorn app.main:app --reload
            ```

            ## Test

            ```bash
            make quality
            ```

            ## PostgreSQL integration

            ```bash
            docker compose up --build
            ```

            For CI-style PostgreSQL testing, set `DATABASE_URL`, `POSTGRES_TEST_DATABASE_URL`,
            and `RUN_POSTGRES_INTEGRATION=1`, then run:

            ```bash
            alembic upgrade head
            pytest
            ```

            ## Load smoke

            ```bash
            make load-smoke
            ```
        """).lstrip()

    def _alembic_files(self, models: dict[str, Any], entity_names: set[str]) -> list[GeneratedFile]:
        files = [
            GeneratedFile(path="alembic.ini", content=self._alembic_ini()),
            GeneratedFile(path="app/db/migrations/env.py", content=self._alembic_env()),
            GeneratedFile(
                path="app/db/migrations/script.py.mako", content=self._alembic_script_template()
            ),
            GeneratedFile(path="app/db/migrations/versions/__init__.py", content=""),
            GeneratedFile(
                path="app/db/migrations/versions/0001_initial.py",
                content=self._alembic_initial_migration(models, entity_names),
            ),
        ]
        return files

    def _alembic_ini(self) -> str:
        return dedent("""
            [alembic]
            script_location = app/db/migrations
            prepend_sys_path = .
            timezone = UTC

            [loggers]
            keys = root,sqlalchemy,alembic

            [handlers]
            keys = console

            [formatters]
            keys = generic

            [logger_root]
            level = WARN
            handlers = console
            qualname =

            [logger_sqlalchemy]
            level = WARN
            handlers =
            qualname = sqlalchemy.engine

            [logger_alembic]
            level = INFO
            handlers =
            qualname = alembic

            [handler_console]
            class = StreamHandler
            args = (sys.stderr,)
            level = NOTSET
            formatter = generic

            [formatter_generic]
            format = %(levelname)-5.5s [%(name)s] %(message)s
            datefmt = %H:%M:%S
        """).lstrip()

    def _alembic_env(self) -> str:
        return dedent("""
            from __future__ import annotations

            from logging.config import fileConfig

            from alembic import context
            from sqlalchemy import engine_from_config, pool

            from app.core.config import get_settings
            from app.db.base import Base
            from app.models import *  # noqa: F403,F401

            config = context.config
            if config.config_file_name is not None:
                fileConfig(config.config_file_name)

            target_metadata = Base.metadata
            settings = get_settings()
            config.set_main_option("sqlalchemy.url", settings.database_url)


            def run_migrations_offline() -> None:
                context.configure(
                    url=settings.database_url,
                    target_metadata=target_metadata,
                    literal_binds=True,
                    dialect_opts={"paramstyle": "named"},
                )
                with context.begin_transaction():
                    context.run_migrations()


            def run_migrations_online() -> None:
                connectable = engine_from_config(
                    config.get_section(config.config_ini_section, {}),
                    prefix="sqlalchemy.",
                    poolclass=pool.NullPool,
                )
                with connectable.connect() as connection:
                    context.configure(connection=connection, target_metadata=target_metadata)
                    with context.begin_transaction():
                        context.run_migrations()


            if context.is_offline_mode():
                run_migrations_offline()
            else:
                run_migrations_online()
        """).lstrip()

    def _alembic_script_template(self) -> str:
        return dedent('''
            """${message}

            Revision ID: ${up_revision}
            Revises: ${down_revision | comma,n}
            Create Date: ${create_date}
            """
            from alembic import op
            import sqlalchemy as sa
            ${imports if imports else ""}

            revision = ${repr(up_revision)}
            down_revision = ${repr(down_revision)}
            branch_labels = ${repr(branch_labels)}
            depends_on = ${repr(depends_on)}


            def upgrade() -> None:
                ${upgrades if upgrades else "pass"}


            def downgrade() -> None:
                ${downgrades if downgrades else "pass"}
        ''').lstrip()

    def _alembic_initial_migration(self, models: dict[str, Any], entity_names: set[str]) -> str:
        upgrade_lines: list[str] = []
        downgrade_lines: list[str] = []
        for name in sorted(entity_names):
            model = models.get(name)
            if not model:
                continue
            table = self._table_name(model.name)
            fields = model.attributes.get("fields", [])
            pk_fields = [f["name"] for f in fields if f.get("primary")]
            unique_fields = [f["name"] for f in fields if f.get("unique")]
            upgrade_lines.append(f"    op.create_table({table!r},")
            for f in fields:
                upgrade_lines.append(f"        {self._migration_column(f)},")
            if pk_fields:
                quoted = ", ".join(repr(x) for x in pk_fields)
                upgrade_lines.append(f"        sa.PrimaryKeyConstraint({quoted}),")
            for field in unique_fields:
                upgrade_lines.append(f"        sa.UniqueConstraint({field!r}),")
            upgrade_lines.append("    )")
            for field in unique_fields:
                upgrade_lines.append(
                    f"    op.create_index('ix_{table}_{field}', {table!r}, [{field!r}], unique=True)"
                )
            for field in reversed(unique_fields):
                downgrade_lines.append(
                    f"    op.drop_index('ix_{table}_{field}', table_name={table!r})"
                )
            downgrade_lines.append(f"    op.drop_table({table!r})")
        if not upgrade_lines:
            upgrade_lines.append("    pass")
        if not downgrade_lines:
            downgrade_lines.append("    pass")
        lines = [
            '"""initial generated schema',
            "",
            "Revision ID: 0001_initial",
            "Revises:",
            "Create Date: 2026-06-29",
            '"""',
            "from __future__ import annotations",
            "",
            "import sqlalchemy as sa",
            "from alembic import op",
            "",
            'revision = "0001_initial"',
            "down_revision = None",
            "branch_labels = None",
            "depends_on = None",
            "",
            "",
            "def upgrade() -> None:",
            *upgrade_lines,
            "",
            "",
            "def downgrade() -> None:",
            *downgrade_lines,
        ]
        return "\n".join(lines) + "\n"

    def _migration_column(self, f: dict[str, Any]) -> str:
        col_type = self._sa_type_name(f)
        if col_type == "String":
            length = f.get("max_length") or (36 if f["python_type"] == "UUID" else 255)
            type_expr = f"sa.String(length={length})"
        elif col_type == "DateTime":
            type_expr = "sa.DateTime(timezone=True)"
        else:
            type_expr = f"sa.{col_type}()"
        args = [
            repr(f["name"]),
            type_expr,
            f"nullable={not bool(f.get('required') or f.get('primary'))}",
        ]
        return f"sa.Column({', '.join(args)})"

    def _indent_lines(self, lines: list[str], spaces: int) -> str:
        prefix = " " * spaces
        return "\n".join(prefix + line if line else "" for line in lines)

    def _indent_text(self, text: str, spaces: int) -> str:
        if not text:
            return ""
        prefix = " " * spaces
        return "\n".join(prefix + line if line else "" for line in text.splitlines())
