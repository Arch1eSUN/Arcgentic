from __future__ import annotations

from pathlib import Path

from arcgentic.agency_roster import parse_agency_roster, select_role_families

FIXTURES = Path(__file__).parents[1] / "fixtures" / "v1"


def test_parses_english_department_role_files() -> None:
    roles = parse_agency_roster(FIXTURES / "agency-en")

    assert len(roles) == 1
    assert roles[0].department == "Engineering"
    assert roles[0].role_name == "Backend Engineer"
    assert roles[0].language == "en"
    assert roles[0].source_path.endswith("engineering/backend-engineer.md")
    assert (
        roles[0].upstream_source
        == "github.com/msitarzewski/agency-agents/engineering/backend-engineer.md"
    )


def test_parses_chinese_catalog_role_paths() -> None:
    roles = parse_agency_roster(FIXTURES / "agency-zh")

    assert len(roles) == 1
    assert roles[0].department == "工程研发"
    assert roles[0].role_name == "后端工程师"
    assert roles[0].language == "zh"
    assert (
        roles[0].upstream_source
        == "github.com/jnMetaCode/agency-agents-zh/工程研发/后端工程师.md"
    )


def test_selects_role_families_for_v1_round() -> None:
    selected = select_role_families(
        ("workflow", "release", "security", "python"),
        available_roles=parse_agency_roster(FIXTURES / "agency-en"),
    )

    assert "minimal-change engineer" in selected
    assert "software architect" in selected
    assert "security engineer" in selected
