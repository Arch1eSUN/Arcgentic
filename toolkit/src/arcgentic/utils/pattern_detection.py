"""Pattern detection utilities for codify-lesson and round-boundary scans."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PatternOccurrence:
    """One finding/debt line extracted from an audit handoff."""

    round_id: str
    source_file: Path
    line_number: int
    priority: str
    text: str


@dataclass(frozen=True)
class PatternCluster:
    """A lexical cluster of repeated audit patterns."""

    signature: str
    occurrences: tuple[PatternOccurrence, ...]

    @property
    def occurrence_count(self) -> int:
        return len(self.occurrences)


_PRIORITY_RE = re.compile(r"\b(P[0-3])\b")
_ROUND_RE = re.compile(r"\b(R\d+(?:[.-][A-Za-z0-9][\w.-]*)?)\b")
_WORD_RE = re.compile(r"[a-z][a-z0-9-]{2,}")
_STOPS = {
    "and",
    "are",
    "but",
    "can",
    "commit",
    "debt",
    "docs",
    "file",
    "finding",
    "for",
    "from",
    "has",
    "line",
    "missing",
    "needs",
    "not",
    "round",
    "that",
    "the",
    "this",
    "with",
}


def scan_last_n_rounds(audit_dir: Path, n: int = 10) -> list[PatternOccurrence]:
    """Extract P2/P3 recurring-pattern candidates from recent audit markdown files."""

    if not audit_dir.exists():
        return []

    files = sorted(
        audit_dir.glob("*.md"),
        key=lambda p: (p.stat().st_mtime, p.name),
        reverse=True,
    )[:n]

    occurrences: list[PatternOccurrence] = []
    for audit_file in files:
        round_id = _round_id_for_file(audit_file)
        occurrences.extend(_scan_structured_finding_rows(audit_file, round_id))
    return occurrences


def cluster_patterns(
    occurrences: list[PatternOccurrence],
    *,
    min_shared_tokens: int = 2,
) -> list[PatternCluster]:
    """Cluster occurrences by token overlap.

    The clustering is intentionally deterministic and lightweight: it is a guardrail
    signal, not an LLM-level semantic classifier.
    """

    clusters: list[list[PatternOccurrence]] = []
    cluster_tokens: list[set[str]] = []

    for occurrence in occurrences:
        tokens = _tokens(occurrence.text)
        if not tokens:
            continue

        best_idx: int | None = None
        best_overlap = 0
        for idx, existing in enumerate(cluster_tokens):
            overlap = len(tokens & existing)
            if overlap > best_overlap:
                best_idx = idx
                best_overlap = overlap

        if best_idx is not None and best_overlap >= min_shared_tokens:
            clusters[best_idx].append(occurrence)
            cluster_tokens[best_idx].update(tokens)
        else:
            clusters.append([occurrence])
            cluster_tokens.append(set(tokens))

    result = [
        PatternCluster(
            signature=_signature_for_cluster(cluster),
            occurrences=tuple(cluster),
        )
        for cluster in clusters
    ]
    return sorted(result, key=lambda c: (-c.occurrence_count, c.signature))


def promote_to_lesson(cluster: PatternCluster, lessons_dir: Path) -> Path:
    """Write a provisional/formal lesson card for a repeated cluster."""

    lessons_dir.mkdir(parents=True, exist_ok=True)
    next_id = _next_lesson_id(lessons_dir)
    slug = _slugify(cluster.signature)
    status = "FORMAL" if cluster.occurrence_count >= 5 else "PROVISIONAL"
    lesson_path = lessons_dir / f"lesson-{next_id}-{slug}.md"
    examples = "\n".join(
        f"  - {o.round_id}: {o.source_file}:{o.line_number} — {o.text}"
        for o in cluster.occurrences
    )
    lesson_path.write_text(
        f"""---
lesson:
  id: {next_id}
  slug: {slug}
  status: {status}
  origin_round: {cluster.occurrences[0].round_id}
  observed_count: {cluster.occurrence_count}
  preservation_streak: "0-of-0"
  novel_preservation_types_seen: []
  mandate_amendments_triggered: []
---

# Lesson {next_id}: {cluster.signature}

## Definition

Repeated audit pattern: {cluster.signature}.

## Examples

{examples}

## Prevention Rule

Before closing a round, check whether `{cluster.signature}` appears in the planned
handoff, implementation notes, self-audit, or external audit evidence.
""",
        encoding="utf-8",
    )
    return lesson_path


def _scan_structured_finding_rows(audit_file: Path, round_id: str) -> list[PatternOccurrence]:
    lines = audit_file.read_text(encoding="utf-8").splitlines()
    occurrences: list[PatternOccurrence] = []
    finding_table: dict[str, int] | None = None

    for idx, line in enumerate(lines, start=1):
        if not line.strip().startswith("|"):
            finding_table = None
            continue

        cells = _split_table_row(line)
        if not cells:
            finding_table = None
            continue
        if _is_table_separator(line):
            continue

        header = _finding_table_header(cells)
        if header is not None:
            finding_table = header
            continue

        if finding_table is None:
            continue

        priority_idx = finding_table["priority"]
        if priority_idx >= len(cells):
            continue
        priority = _extract_priority(cells[priority_idx])
        if priority not in {"P2", "P3"}:
            continue

        text = _structured_finding_text(cells, finding_table)
        if not text:
            continue
        occurrences.append(
            PatternOccurrence(
                round_id=round_id,
                source_file=audit_file,
                line_number=idx,
                priority=priority,
                text=text,
            )
        )

    return occurrences


def _finding_table_header(cells: list[str]) -> dict[str, int] | None:
    normalized = [_normalize_header(cell) for cell in cells]
    if "priority" not in normalized:
        return None
    summary_idx = _first_index(normalized, {"summary", "finding", "description"})
    if summary_idx is None:
        return None
    return {
        "id": _first_index(normalized, {"id", "finding id"}) or 0,
        "priority": normalized.index("priority"),
        "summary": summary_idx,
        "evidence": _first_index(normalized, {"evidence", "location"}) or summary_idx,
    }


def _structured_finding_text(cells: list[str], header: dict[str, int]) -> str:
    parts: list[str] = []
    for key in ("id", "summary", "evidence"):
        idx = header[key]
        if idx < len(cells):
            value = cells[idx].strip()
            if value:
                parts.append(value)
    return " ".join(parts)


def _split_table_row(line: str) -> list[str]:
    sentinel = "\x00PIPE\x00"
    safe = line.strip().replace(r"\|", sentinel)
    if not safe.startswith("|"):
        return []
    return [cell.replace(sentinel, "|").strip(" `") for cell in safe.strip("|").split("|")]


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("_", " "))


def _first_index(values: list[str], candidates: set[str]) -> int | None:
    for idx, value in enumerate(values):
        if value in candidates:
            return idx
    return None


def _extract_priority(value: str) -> str | None:
    match = _PRIORITY_RE.search(value)
    return match.group(1) if match else None


def _round_id_for_file(path: Path) -> str:
    match = _ROUND_RE.search(path.stem)
    return match.group(1) if match else path.stem


def _is_table_separator(line: str) -> bool:
    stripped = line.strip().replace("|", "").replace("-", "").replace(":", "")
    return stripped == ""


def _tokens(text: str) -> set[str]:
    words = _WORD_RE.findall(text.lower())
    return {word for word in words if word not in _STOPS and not word.startswith("p")}


def _signature_for_cluster(cluster: list[PatternOccurrence]) -> str:
    counts: Counter[str] = Counter()
    for occurrence in cluster:
        counts.update(_tokens(occurrence.text))
    selected = [word for word, _ in counts.most_common(5)]
    return " ".join(selected) if selected else "unclassified-pattern"


def _next_lesson_id(lessons_dir: Path) -> int:
    ids: list[int] = []
    for path in lessons_dir.glob("lesson-*-*.md"):
        parts = path.stem.split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            ids.append(int(parts[1]))
    return max(ids, default=0) + 1


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unclassified-pattern"
