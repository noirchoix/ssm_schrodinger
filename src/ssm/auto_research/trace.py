from __future__ import annotations

import json
import time
import uuid
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from ssm.auto_research.hashing import sha256_value
from ssm.auto_research.schemas import (
    DeterminismCensusReport,
    ReplayComparison,
    ReplayMismatch,
    SignatureCensus,
    TraceDocument,
    TraceHeader,
    TraceSpan,
    TraceTaskOutput,
)

_EFFECTFUL = {"model_call", "tool_call", "env_read", "memory_op", "branch"}


class TraceValidationError(ValueError):
    pass


class _SpanContext(AbstractContextManager["_SpanContext"]):
    def __init__(
        self,
        recorder: TraceRecorder,
        kind: str,
        name: str,
        input_value: Any,
        attrs: dict[str, str] | None,
        parent_span_id: int | None,
    ) -> None:
        self.recorder = recorder
        self.kind = kind
        self.name = name
        self.input_value = input_value
        self.attrs = attrs or {}
        self.parent_span_id = parent_span_id
        self.output: Any = None
        self.error: str | None = None
        self.started_at_ms = 0
        self.span_id = 0
        self.seq = 0

    def __enter__(self) -> _SpanContext:
        self.started_at_ms = int(time.time() * 1000)
        self.span_id, self.seq = self.recorder._allocate()
        return self

    def set_output(self, value: Any) -> None:
        self.output = value

    def set_error(self, value: BaseException | str) -> None:
        self.error = str(value)

    def __exit__(
        self, exc_type: object, exc: BaseException | None, traceback: object
    ) -> Literal[False]:
        if exc is not None and self.error is None:
            self.error = str(exc)
        duration = max(0, int(time.time() * 1000) - self.started_at_ms)
        span = TraceSpan(
            trace_id=self.recorder.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            seq=self.seq,
            kind=self.kind,  # type: ignore[arg-type]
            name=self.name,
            input=self.input_value,
            output=self.output,
            error=self.error,
            started_at_ms=self.started_at_ms,
            duration_ms=duration,
            attrs=self.attrs,
        )
        self.recorder._append(span.model_dump(mode="json"))
        return False


class TraceRecorder:
    """Strict append-only Auto-compatible trace recorder for SSM research runs."""

    def __init__(
        self,
        path: str | Path,
        *,
        task: str,
        task_input: Any | None = None,
        attrs: dict[str, str] | None = None,
        trace_id: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_id = trace_id or uuid.uuid4().hex
        self.task = task
        self._next_id = 1
        self._task_output_set = False
        self.header = TraceHeader(
            trace_id=self.trace_id,
            task=task,
            started_at_ms=int(time.time() * 1000),
            attrs=attrs or {},
            task_input=task_input,
        )
        self.path.write_text(
            json.dumps(self.header.model_dump(mode="json", exclude_none=True), sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    def _allocate(self) -> tuple[int, int]:
        current = self._next_id
        self._next_id += 1
        return current, current

    def _append(self, payload: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")

    def span(
        self,
        kind: str,
        name: str,
        *,
        input_value: Any = None,
        attrs: dict[str, str] | None = None,
        parent_span_id: int | None = None,
    ) -> _SpanContext:
        return _SpanContext(self, kind, name, input_value, attrs, parent_span_id)

    def record(
        self,
        kind: str,
        name: str,
        *,
        input_value: Any = None,
        output: Any = None,
        error: str | None = None,
        duration_ms: int = 0,
        attrs: dict[str, str] | None = None,
        parent_span_id: int | None = None,
    ) -> TraceSpan:
        span_id, seq = self._allocate()
        span = TraceSpan(
            trace_id=self.trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            seq=seq,
            kind=kind,  # type: ignore[arg-type]
            name=name,
            input=input_value,
            output=output,
            error=error,
            started_at_ms=int(time.time() * 1000),
            duration_ms=max(0, duration_ms),
            attrs=attrs or {},
        )
        self._append(span.model_dump(mode="json"))
        return span

    def set_task_output(self, output: Any) -> None:
        if self._task_output_set:
            raise TraceValidationError("Task output may be recorded at most once.")
        if output is None:
            raise TraceValidationError(
                "A null task output is treated as absent and cannot be recorded."
            )
        task_output = TraceTaskOutput(
            trace_id=self.trace_id,
            output=output,
            recorded_at_ms=int(time.time() * 1000),
        )
        self._append(task_output.model_dump(mode="json"))
        self._task_output_set = True


def load_trace(path: str | Path) -> TraceDocument:
    lines = [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise TraceValidationError("Trace is empty.")
    try:
        first = json.loads(lines[0])
        header = TraceHeader.model_validate(first)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise TraceValidationError(f"Invalid trace header: {exc}") from exc
    spans: list[TraceSpan] = []
    task_output: TraceTaskOutput | None = None
    span_ids: set[int] = set()
    seqs: set[int] = set()
    for raw in lines[1:]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TraceValidationError(f"Invalid trace JSONL line: {exc}") from exc
        if payload.get("t") == "span":
            try:
                span = TraceSpan.model_validate(payload)
            except ValidationError as exc:
                raise TraceValidationError(f"Invalid trace span: {exc}") from exc
            if span.trace_id != header.trace_id:
                raise TraceValidationError("Span trace_id differs from header.")
            if span.span_id in span_ids or span.seq in seqs:
                raise TraceValidationError("Duplicate span_id or seq.")
            if span.parent_span_id is not None and span.parent_span_id not in span_ids:
                raise TraceValidationError("Parent span does not exist or did not open earlier.")
            span_ids.add(span.span_id)
            seqs.add(span.seq)
            spans.append(span)
        elif payload.get("t") == "task_output":
            if task_output is not None:
                raise TraceValidationError("Duplicate task_output line.")
            try:
                task_output = TraceTaskOutput.model_validate(payload)
            except ValidationError as exc:
                raise TraceValidationError(f"Invalid task output: {exc}") from exc
            if task_output.trace_id != header.trace_id:
                raise TraceValidationError("Task output trace_id differs from header.")
        else:
            raise TraceValidationError(f"Unknown trace line type: {payload.get('t')!r}")
    spans.sort(key=lambda item: item.seq)
    return TraceDocument(header=header, spans=spans, task_output=task_output)


def determinism_census(paths: list[str | Path]) -> DeterminismCensusReport:
    documents = [load_trace(path) for path in paths]
    if not documents:
        raise TraceValidationError("At least one trace is required.")
    tasks = {item.header.task for item in documents}
    if len(tasks) != 1:
        raise TraceValidationError("All traces in one census must have the same task label.")
    grouped: dict[tuple[str, str, str], list[TraceSpan]] = {}
    for document in documents:
        for span in document.spans:
            if span.kind not in _EFFECTFUL:
                continue
            key = (span.kind, span.name, sha256_value(span.input))
            grouped.setdefault(key, []).append(span)
    signature_rows: list[SignatureCensus] = []
    total = 0
    witnessed = 0
    deterministic = 0
    divergent = 0
    for (kind, name, input_digest), observations in sorted(grouped.items()):
        count = len(observations)
        total += count
        errors = sum(item.error is not None for item in observations)
        outputs = {sha256_value(item.output) for item in observations}
        classification: Literal["WITNESSED_DETERMINISTIC", "WITNESSED_DIVERGENT", "UNWITNESSED"]
        if count < 2:
            classification = "UNWITNESSED"
        elif errors == 0 and len(outputs) == 1:
            classification = "WITNESSED_DETERMINISTIC"
            witnessed += count
            deterministic += count
        else:
            classification = "WITNESSED_DIVERGENT"
            witnessed += count
            divergent += count
        signature_rows.append(
            SignatureCensus(
                kind=kind,
                name=name,
                input_sha256=input_digest,
                observations=count,
                errors=errors,
                distinct_outputs=len(outputs),
                classification=classification,
            )
        )
    return DeterminismCensusReport.create(
        task=next(iter(tasks)),
        traces=len(documents),
        effectful_observations=total,
        witnessed_observations=witnessed,
        deterministic_observations=deterministic,
        divergent_observations=divergent,
        witnessed_coverage=(witnessed / total if total else None),
        deterministic_fraction=(deterministic / witnessed if witnessed else None),
        signatures=signature_rows,
    )


def compare_traces(baseline_path: str | Path, candidate_path: str | Path) -> ReplayComparison:
    baseline = load_trace(baseline_path)
    candidate = load_trace(candidate_path)
    base_spans = [item for item in baseline.spans if item.kind in _EFFECTFUL]
    candidate_spans = [item for item in candidate.spans if item.kind in _EFFECTFUL]
    mismatches: list[ReplayMismatch] = []
    matched = 0
    maximum = max(len(base_spans), len(candidate_spans))
    for index in range(maximum):
        left = base_spans[index] if index < len(base_spans) else None
        right = candidate_spans[index] if index < len(candidate_spans) else None
        left_signature = _signature(left) if left else None
        right_signature = _signature(right) if right else None
        if left is None or right is None:
            mismatches.append(
                ReplayMismatch(
                    index=index,
                    reason="effectful span count differs",
                    baseline_signature=left_signature,
                    candidate_signature=right_signature,
                )
            )
            continue
        if left_signature != right_signature:
            mismatches.append(
                ReplayMismatch(
                    index=index,
                    reason="call signature differs",
                    baseline_signature=left_signature,
                    candidate_signature=right_signature,
                )
            )
            continue
        if left.error != right.error or sha256_value(left.output) != sha256_value(right.output):
            mismatches.append(
                ReplayMismatch(
                    index=index,
                    reason="recorded outcome differs",
                    baseline_signature=left_signature,
                    candidate_signature=right_signature,
                )
            )
            continue
        matched += 1
    return ReplayComparison(
        baseline_trace_id=baseline.header.trace_id,
        candidate_trace_id=candidate.header.trace_id,
        matched=matched,
        mismatches=mismatches,
        equivalent=not mismatches,
    )


def _signature(span: TraceSpan) -> str:
    return f"{span.kind}:{span.name}:{sha256_value(span.input)}"
