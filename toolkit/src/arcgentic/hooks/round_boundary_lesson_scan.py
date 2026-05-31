"""Round-boundary lesson-scan hook."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from arcgentic.skills_impl.codify_lesson import run as codify_lesson_run
from arcgentic.utils.pattern_detection import cluster_patterns, scan_last_n_rounds

DEFAULT_N = 10
MIN_OCCURRENCES_FOR_PROVISIONAL = 3


@dataclass(frozen=True)
class RoundBoundaryLessonScanResult:
    scanned: int
    promotable_clusters: int
    lesson_count: int
    exit_code: int = 0

    def summary(self) -> str:
        return (
            "round-boundary-lesson-scan: "
            f"{self.promotable_clusters} promotable clusters, "
            f"{self.lesson_count} lessons, scanned {self.scanned} occurrences"
        )


def run(
    *,
    audit_dir: Path,
    lessons_dir: Path,
    amendments_dir: Path,
    n: int = DEFAULT_N,
    dry_run: bool = False,
) -> RoundBoundaryLessonScanResult:
    occurrences = scan_last_n_rounds(audit_dir, n)
    clusters = cluster_patterns(occurrences)
    promotable = [
        cluster
        for cluster in clusters
        if cluster.occurrence_count >= MIN_OCCURRENCES_FOR_PROVISIONAL
    ]
    lesson_count = 0
    if promotable and not dry_run:
        result = codify_lesson_run(
            audit_dir=audit_dir,
            lessons_dir=lessons_dir,
            amendments_dir=amendments_dir,
            n=n,
        )
        lesson_count = len(result.lessons)
    return RoundBoundaryLessonScanResult(
        scanned=len(occurrences),
        promotable_clusters=len(promotable),
        lesson_count=lesson_count,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arcgentic round-boundary-lesson-scan")
    parser.add_argument("--N", type=int, default=DEFAULT_N)
    parser.add_argument("--audit-dir", default="docs/audits")
    parser.add_argument("--lessons-dir", default="lessons")
    parser.add_argument("--amendments-dir", default="mandates/amendments")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = run(
        audit_dir=Path(args.audit_dir),
        lessons_dir=Path(args.lessons_dir),
        amendments_dir=Path(args.amendments_dir),
        n=args.N,
        dry_run=args.dry_run,
    )
    print(result.summary())
    return result.exit_code

