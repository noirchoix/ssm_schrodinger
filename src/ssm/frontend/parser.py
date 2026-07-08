from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ssm.errors import CompilerDiagnostic, SMLSyntaxError
from ssm.models import Directive, SMLDocument, SMLSection, SourceRange

_SECTION_RE = re.compile(r"^#(?P<type>[A-Za-z][A-Za-z0-9_]*)(?:\s+(?P<name>.*?))?\s*$")
_DIRECTIVE_RE = re.compile(r"^@(?P<name>[A-Za-z][A-Za-z0-9_]*)(?:\s+(?P<args>.*?))?\s*$")
_KEY_VALUE_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(?P<value>.*)$")


class SMLParser:
    """Line-oriented parser for the SML Markdown subset.

    The parser intentionally accepts a narrow, deterministic subset rather than
    attempting to be Markdown-compatible. This keeps SML compiler-safe while
    remaining readable.
    """

    def parse_file(self, path: str | Path) -> SMLDocument:
        p = Path(path)
        return self.parse_text(p.read_text(encoding="utf-8"), source_file=str(p))

    def parse_text(self, text: str, source_file: str = "<memory>") -> SMLDocument:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        directives: list[Directive] = []
        sections: list[SMLSection] = []
        i = 0
        seen_section = False
        while i < len(lines):
            raw = lines[i]
            stripped = raw.strip()
            line_no = i + 1
            if not stripped or stripped.startswith("//") or stripped.startswith("<!--"):
                i += 1
                continue
            if stripped.startswith("@"):
                if seen_section:
                    self._syntax(
                        source_file,
                        line_no,
                        "SML001",
                        "Compiler directives must appear before sections.",
                    )
                m = _DIRECTIVE_RE.match(stripped)
                if not m:
                    self._syntax(
                        source_file, line_no, "SML002", f"Invalid directive syntax: {stripped}"
                    )
                if m is None:
                    raise RuntimeError("unreachable parser state")
                directives.append(
                    Directive(
                        name=m.group("name"),
                        args=(m.group("args") or "").strip() or None,
                        source_range=SourceRange(
                            file=source_file, start_line=line_no, end_line=line_no
                        ),
                    )
                )
                i += 1
                continue
            if stripped.startswith("#"):
                seen_section = True
                m = _SECTION_RE.match(stripped)
                if not m:
                    self._syntax(
                        source_file, line_no, "SML003", f"Invalid section heading: {stripped}"
                    )
                if m is None:
                    raise RuntimeError("unreachable parser state")
                section_type = m.group("type")
                name = (m.group("name") or "").strip() or None
                start = line_no
                body: list[tuple[int, str]] = []
                i += 1
                while i < len(lines):
                    nxt = lines[i]
                    if nxt.strip().startswith("#"):
                        break
                    body.append((i + 1, nxt))
                    i += 1
                end = body[-1][0] if body else start
                fields = self._parse_body(body, source_file)
                sections.append(
                    SMLSection(
                        section_type=section_type,
                        name=name,
                        fields=fields,
                        source_range=SourceRange(file=source_file, start_line=start, end_line=end),
                    )
                )
                continue
            self._syntax(
                source_file, line_no, "SML004", f"Expected directive or section, got: {stripped}"
            )
        return SMLDocument(source_file=source_file, directives=directives, sections=sections)

    def _parse_body(self, body: list[tuple[int, str]], source_file: str) -> dict[str, Any]:
        # Remove blank and comment lines while preserving line numbers.
        filtered: list[tuple[int, int, str]] = []
        for line_no, raw in body:
            if "\t" in raw:
                self._syntax(
                    source_file, line_no, "SML005", "Tabs are not allowed for indentation."
                )
            stripped = raw.strip()
            if not stripped or stripped.startswith("//"):
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            filtered.append((line_no, indent, stripped))
        result: dict[str, Any] = {}
        i = 0
        while i < len(filtered):
            line_no, indent, text = filtered[i]
            if indent != 0:
                self._syntax(
                    source_file, line_no, "SML006", "Top-level section fields must not be indented."
                )
            m = _KEY_VALUE_RE.match(text)
            if not m:
                self._syntax(
                    source_file, line_no, "SML007", f"Expected key-value field, got: {text}"
                )
            if m is None:
                raise RuntimeError("unreachable parser state")
            key = m.group("key")
            value = m.group("value")
            if value == "":
                nested: list[tuple[int, int, str]] = []
                i += 1
                while i < len(filtered) and filtered[i][1] > indent:
                    nested.append(filtered[i])
                    i += 1
                result[key] = self._parse_nested(nested, source_file, parent_key=key)
            else:
                result[key] = self._parse_scalar(value)
                i += 1
        return result

    def _parse_nested(
        self, lines: list[tuple[int, int, str]], source_file: str, parent_key: str
    ) -> Any:
        if not lines:
            return []
        min_indent = min(indent for _, indent, _ in lines)
        normalized = [(ln, indent - min_indent, text) for ln, indent, text in lines]
        if all(text.startswith("- ") for _, indent, text in normalized if indent == 0):
            items: list[Any] = []
            for line_no, indent, text in normalized:
                if indent != 0:
                    # MVP: nested blocks under list items are not supported.
                    self._syntax(
                        source_file,
                        line_no,
                        "SML008",
                        f"Nested list blocks under '{parent_key}' are not supported in V1.",
                    )
                items.append(self._parse_scalar(text[2:].strip()))
            return items
        mapping: dict[str, Any] = {}
        i = 0
        while i < len(normalized):
            line_no, indent, text = normalized[i]
            if indent != 0:
                self._syntax(
                    source_file,
                    line_no,
                    "SML009",
                    f"Unexpected nested indentation under '{parent_key}'.",
                )
            m = _KEY_VALUE_RE.match(text)
            if not m:
                self._syntax(
                    source_file,
                    line_no,
                    "SML010",
                    f"Expected nested key-value under '{parent_key}', got: {text}",
                )
            if m is None:
                raise RuntimeError("unreachable parser state")
            key = m.group("key")
            value = m.group("value")
            if value == "":
                child: list[tuple[int, int, str]] = []
                i += 1
                while i < len(normalized) and normalized[i][1] > indent:
                    child.append(normalized[i])
                    i += 1
                mapping[key] = self._parse_nested(
                    [(ln, ind + 2, tx) for ln, ind, tx in child], source_file, key
                )
            else:
                mapping[key] = self._parse_scalar(value)
                i += 1
        return mapping

    def _parse_scalar(self, value: str) -> Any:
        value = value.strip()
        if value == "":
            return ""
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none"}:
            return None
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                return []
            return [self._parse_scalar(part.strip()) for part in inner.split(",")]
        if re.fullmatch(r"[-+]?\d+", value):
            try:
                return int(value)
            except ValueError:
                pass
        if re.fullmatch(r"[-+]?\d+\.\d+", value):
            try:
                return float(value)
            except ValueError:
                pass
        return value

    def _syntax(self, source_file: str, line_no: int, code: str, message: str) -> None:
        raise SMLSyntaxError(
            CompilerDiagnostic(
                code=code,
                message=message,
                file=source_file,
                start_line=line_no,
                end_line=line_no,
            )
        )
