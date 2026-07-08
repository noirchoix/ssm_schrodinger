from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class CompilerDiagnostic:
    code: str
    message: str
    severity: str = "error"
    file: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    node_id: str | None = None
    suggested_fix: str | None = None

    def render(self) -> str:
        loc = ""
        if self.file and self.start_line:
            loc = f"{self.file}:{self.start_line}"
        prefix = f"{self.severity.upper()} {self.code}"
        body = f"{prefix}: {self.message}"
        if loc:
            body += f"\n  at {loc}"
        if self.suggested_fix:
            body += f"\n  suggested fix: {self.suggested_fix}"
        return body


class SSMError(Exception):
    """Base compiler exception."""


class SMLSyntaxError(SSMError):
    def __init__(self, diagnostic: CompilerDiagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.render())


class SemanticError(SSMError):
    def __init__(self, diagnostics: Iterable[CompilerDiagnostic]):
        self.diagnostics = list(diagnostics)
        super().__init__("\n".join(d.render() for d in self.diagnostics))


class ResolutionError(SSMError):
    def __init__(self, diagnostics: Iterable[CompilerDiagnostic]):
        self.diagnostics = list(diagnostics)
        super().__init__("\n".join(d.render() for d in self.diagnostics))
