"""codify-lesson skill implementation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from arcgentic.utils.pattern_detection import (
    PatternCluster,
    cluster_patterns,
    promote_to_lesson,
    scan_last_n_rounds,
)


@dataclass(frozen=True)
class CodifyLessonResult:
    lessons: list[Path]
    amendments: list[Path]
    updated_streaks: list[Path]
    exit_code: int = 0
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "codify-lesson completed:",
            f"  lessons: {len(self.lessons)}",
            f"  amendments: {len(self.amendments)}",
            f"  streak_updates: {len(self.updated_streaks)}",
        ]
        for path in [*self.lessons, *self.amendments, *self.updated_streaks]:
            lines.append(f"  - {path}")
        for warning in self.warnings:
            lines.append(f"  warning: {warning}")
        return "\n".join(lines)


def run(
    *,
    audit_dir: Path,
    lessons_dir: Path,
    amendments_dir: Path,
    n: int = 10,
    min_occurrences: int = 3,
    formal_occurrences: int = 5,
    dry_run: bool = False,
) -> CodifyLessonResult:
    """Detect recurring audit patterns and write lesson cards."""

    occurrences = scan_last_n_rounds(audit_dir, n)
    clusters = cluster_patterns(occurrences)
    qualifying = [cluster for cluster in clusters if cluster.occurrence_count >= min_occurrences]

    lessons: list[Path] = []
    amendments: list[Path] = []
    if not dry_run:
        for cluster in qualifying:
            lesson_path = promote_to_lesson(cluster, lessons_dir)
            lessons.append(lesson_path)
            if cluster.occurrence_count >= formal_occurrences:
                amendments.append(_write_amendment(cluster.signature, amendments_dir))

    updated_streaks = [] if dry_run else _update_preservation_streaks(lessons_dir, qualifying)
    return CodifyLessonResult(
        lessons=lessons,
        amendments=amendments,
        updated_streaks=updated_streaks,
        warnings=[] if qualifying else ["no clusters met the promotion threshold"],
    )


def _write_amendment(signature: str, amendments_dir: Path) -> Path:
    amendments_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", signature.lower()).strip("-") or "pattern"
    path = amendments_dir / f"amendment-{slug}.md"
    path.write_text(
        f"""# Mandate Amendment Proposal: {signature}

## Trigger

Pattern reached formal threshold during codify-lesson scan.

## Proposed Amendment

Add an explicit pre-close check for `{signature}` to the relevant round handoff and
audit verdict templates.
""",
        encoding="utf-8",
    )
    return path


def _update_preservation_streaks(
    lessons_dir: Path,
    active_clusters: list[PatternCluster],
) -> list[Path]:
    active_text = " ".join(getattr(cluster, "signature", "") for cluster in active_clusters)
    updated: list[Path] = []
    for lesson_path in lessons_dir.glob("lesson-*-*.md"):
        text = lesson_path.read_text(encoding="utf-8")
        slug_match = re.search(r"slug:\s+([a-z0-9-]+)", text)
        if slug_match and slug_match.group(1).replace("-", " ") in active_text:
            continue
        streak_match = re.search(r'preservation_streak:\s+"(\d+)-of-(\d+)"', text)
        if not streak_match:
            continue
        kept = int(streak_match.group(1)) + 1
        total = int(streak_match.group(2)) + 1
        updated_text = re.sub(
            r'preservation_streak:\s+"\d+-of-\d+"',
            f'preservation_streak: "{kept}-of-{total}"',
            text,
            count=1,
        )
        lesson_path.write_text(updated_text, encoding="utf-8")
        updated.append(lesson_path)
    return updated
