"""track-refs skill implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class UnclassifiableReferenceError(ValueError):
    """Raised when usage evidence is insufficient for RT classification."""


UnclassifiableReference = UnclassifiableReferenceError


@dataclass(frozen=True)
class ReferenceEntry:
    owner_repo: str
    repo_path: Path
    license_name: str
    categories: list[str]
    description: str
    relevance: str
    rt_tier: str
    key_paths: list[str] = field(default_factory=list)

    def to_index_block(self, round_name: str) -> str:
        key_paths = "\n".join(
            f"  - `{path}` — inspect for reusable shape"
            for path in self.key_paths
        )
        if not key_paths:
            key_paths = "  - `README*` — inspect project overview"
        return f"""### `{self.owner_repo}` (`{self.repo_path}/`, {self.license_name})
- **CATEGORY**: {"; ".join(self.categories)}
- **Desc**: {self.description}
- **{round_name}-relevance**: {self.relevance}
- **License + RT**: {self.license_name} + {self.rt_tier}
- **Key paths**:
{key_paths}
"""


def classify_reference(
    repo_path: str,
    license_str: str,
    usage_evidence: dict[str, bool],
) -> str:
    """Return RT tier classification: RT0 / RT1 / RT2 / RT3."""

    if usage_evidence.get("imported_at_runtime"):
        return "RT3"
    if usage_evidence.get("binary_vendored"):
        return "RT2"
    if usage_evidence.get("code_adapted"):
        if any(viral in license_str.upper() for viral in ["AGPL", "GPL"]):
            return "RT0"
        return "RT1"
    if usage_evidence.get("pattern_only"):
        return "RT0"
    raise UnclassifiableReference(repo_path)


def detect_category_tags(repo_path: Path) -> list[str]:
    """Infer coarse scan tags from common repo files and directories."""

    tags: set[str] = set()
    names = {p.name.lower() for p in repo_path.iterdir()} if repo_path.exists() else set()
    suffixes = {p.suffix.lower() for p in repo_path.rglob("*") if p.is_file()}

    if "package.json" in names:
        tags.add("javascript")
    if "pyproject.toml" in names or ".py" in suffixes:
        tags.add("python")
    if "go.mod" in names:
        tags.add("go")
    if "src" in names:
        tags.add("source-layout")
    if "tests" in names or "test" in names:
        tags.add("test-patterns")
    if "docs" in names:
        tags.add("documentation")
    if ".md" in suffixes:
        tags.add("markdown")
    return sorted(tags or {"uncategorized"})


def license_name(repo_path: Path) -> str:
    """Best-effort license label from common license files."""

    for candidate in ["LICENSE", "LICENSE.md", "COPYING"]:
        path = repo_path / candidate
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="ignore").upper()
            if "AGPL" in content:
                return "AGPL"
            if "GNU GENERAL PUBLIC LICENSE" in content or "\nGPL" in content:
                return "GPL"
            if "MIT LICENSE" in content:
                return "MIT"
            if "APACHE LICENSE" in content:
                return "Apache-2.0"
            if "BSD" in content:
                return "BSD"
            return "UNKNOWN"
    return "NOASSERTION"


def build_reference_entry(
    *,
    repo_path: Path,
    owner_repo: str,
    round_name: str,
    usage_evidence: dict[str, bool],
    relevance: str = "medium",
) -> ReferenceEntry:
    """Build a categorized reference entry for references/INDEX.md."""

    lic = license_name(repo_path)
    return ReferenceEntry(
        owner_repo=owner_repo,
        repo_path=repo_path,
        license_name=lic,
        categories=detect_category_tags(repo_path),
        description=_description(repo_path),
        relevance=relevance,
        rt_tier=classify_reference(str(repo_path), lic, usage_evidence),
        key_paths=_key_paths(repo_path),
    )


def append_to_index(index_path: Path, entry: ReferenceEntry, round_name: str) -> None:
    """Append a repo block to references/INDEX.md, creating the header if needed."""

    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_path.exists():
        index_path.write_text(_index_header(), encoding="utf-8")
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write("\n")
        handle.write(entry.to_index_block(round_name))


def emit_triplet_table(entries: list[ReferenceEntry]) -> str:
    """Emit BA-design-ready 4-column triplet table."""

    lines = [
        "| # | 用了哪个 | 为什么用 | 用了什么部分 | License + RT |",
        "|---|---|---|---|---|",
    ]
    for idx, entry in enumerate(entries, start=1):
        key_path = entry.key_paths[0] if entry.key_paths else "README*"
        lines.append(
            "| {idx} | `{repo}` + `{path}` | {why} | {part} | {license} + {rt} |".format(
                idx=idx,
                repo=entry.owner_repo,
                path=key_path,
                why=entry.description,
                part="; ".join(entry.categories),
                license=entry.license_name,
                rt=entry.rt_tier,
            )
        )
    return "\n".join(lines)


def refresh_relevance(index_path: Path, round_name: str, default_relevance: str = "none") -> int:
    """Ensure each repo block has a relevance line for the current round."""

    if not index_path.exists():
        return 0
    lines = index_path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    changes = 0
    pending_block = False
    relevance_marker = f"**{round_name}-relevance**"
    for line in lines:
        if line.startswith("### `"):
            pending_block = True
        if pending_block and relevance_marker in line:
            pending_block = False
        if pending_block and line.startswith("- **Key paths**:"):
            updated.append(f"- **{round_name}-relevance**: {default_relevance}")
            pending_block = False
            changes += 1
        updated.append(line)
    index_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return changes


def usage_evidence_from_json(value: str) -> dict[str, bool]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("usage evidence must be a JSON object")
    return {str(key): bool(item) for key, item in parsed.items()}


def _description(repo_path: Path) -> str:
    for candidate in ["README.md", "README"]:
        path = repo_path / candidate
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip(" #")
                if stripped:
                    return stripped[:120]
    return "Reference repository"


def _key_paths(repo_path: Path) -> list[str]:
    keys: list[str] = []
    for candidate in ["README.md", "src", "tests", "docs"]:
        if (repo_path / candidate).exists():
            keys.append(candidate)
    return keys


def _index_header() -> str:
    return """# references/INDEX.md — categorized scan-friendly index

> Gitignored reference material; do not import at runtime without explicit RT review.
"""
