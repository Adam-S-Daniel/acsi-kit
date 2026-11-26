"""The required-checks table in docs/settings-and-apps.md matches fleet.yml.

The page's `Repo | Required checks` table tells an adopter which checks each
repo's ruleset requires. The shipped
`starter/repo-settings/repo-settings/fleet.yml` decides it: a repo's
`overrides.ruleset.required_status_checks` replaces the default's list.
These tests resolve that file with the shipped engine's own
`load_config` and `resolve_targets` (never a reimplementation of the merge),
after adding skills-evals' element from `fleet.evals.yml` the way
`bootstrap/regenerate.sh evals-fleet` does (`bootstrap/lib/fleet_fragment.py`),
because the table covers the evals track too. The page is parsed with
markdown-it-py and the YAML with PyYAML; no regex reads either.

So a source change to a repo's required checks fails here until the page
follows, and the re-sync holds that source back (MAINTAINING.md).

Run: python3 -m pytest export/tests/test_required_checks_table.py -q
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

KIT = Path(__file__).resolve().parents[2]
PAGE = KIT / "docs/settings-and-apps.md"
STARTER = KIT / "starter/repo-settings"
FLEET = STARTER / "repo-settings/fleet.yml"
FRAGMENT = STARTER / "repo-settings/fleet.evals.yml"
HEADER = ["Repo", "Required checks"]

# fleet.yml names its bypass Apps as "${NAME}" (DECISIONS C12), and the
# engine refuses to resolve a ruleset without them. Invented ids.
APP_IDS = {"GUIDANCE_SYNC_APP_ID": "900001", "ROSTER_WRITER_APP_ID": "900003"}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rs = _load("kit_test_repo_settings_engine", STARTER / "scripts/repo_settings.py")
ff = _load("kit_test_fleet_fragment", KIT / "bootstrap/lib/fleet_fragment.py")


# ---------------------------------------------------------------- the page

def _code_names(cell, where: str) -> list[str]:
    """The inline-code spans of a table cell. Anything else in it but commas
    and spaces fails: a check written without backticks would otherwise be
    read as no check at all."""
    names = []
    for child in cell.children or []:
        if child.type == "code_inline":
            names.append(child.content)
        elif child.type == "text" and not child.content.replace(",", "").strip():
            continue
        else:
            raise AssertionError(f"{where}: unexpected {child.type} {child.content!r}; "
                                 "write each name in backticks, separated by commas")
    return names


def table_rows(text: str) -> dict[str, list[str]]:
    """{repo: [checks]} from the one table whose header is `Repo | Required checks`."""
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    tables, rows, row, in_table = [], [], [], False
    for i, t in enumerate(tokens):
        if t.type == "table_open":
            in_table, rows = True, []
        elif in_table and t.type in ("th_open", "td_open"):
            row.append(tokens[i + 1])
        elif in_table and t.type == "tr_close":
            rows.append(row)
            row = []
        elif t.type == "table_close":
            in_table = False
            if [c.content.strip() for c in rows[0]] == HEADER:
                tables.append(rows[1:])
    assert len(tables) == 1, f"expected one `Repo | Required checks` table, found {len(tables)}"
    out: dict[str, list[str]] = {}
    for repo_cell, checks_cell in tables[0]:
        repo = _code_names(repo_cell, "a Repo cell")
        assert len(repo) == 1, f"a Repo cell must name one repo in backticks (got {repo_cell.content!r})"
        assert repo[0] not in out, f"{repo[0]} has two rows"
        out[repo[0]] = _code_names(checks_cell, f"{repo[0]}'s Required checks cell")
    return out


# ---------------------------------------------------------------- the fleet

def fleet_checks(fleet_text: str, fragment_text: str | None, tmp_path: Path) -> dict[str, list[str]]:
    """{repo (no owner): required checks} for every repo whose resolved,
    managed settings enable a ruleset, as the engine resolves them."""
    if fragment_text is not None:
        fleet_text, _ = ff.merged(fleet_text, fragment_text)
    path = tmp_path / "fleet.yml"
    path.write_text(fleet_text, encoding="utf-8")
    out: dict[str, list[str]] = {}
    for target in rs.resolve_targets(rs.load_config(str(path)), None):
        # `effective`: what the engine plans, so a `manage` that leaves the
        # ruleset out (the label-only site repos) has no row to match.
        ruleset = target["effective"].get("ruleset") or {}
        if not ruleset.get("enabled"):
            continue
        short = target["repo"].split("/", 1)[1]
        assert short not in out, f"two owners declare {short}; the table cannot tell them apart"
        out[short] = list(ruleset.get("required_status_checks") or [])
    return out


def differences(table: dict[str, list[str]], fleet: dict[str, list[str]]) -> list[str]:
    """One line per repo whose row and fleet.yml disagree. Order is ignored:
    GitHub requires a set of checks."""
    out = []
    for repo in sorted(set(table) | set(fleet)):
        if repo not in fleet:
            out.append(f"{repo}: the table lists {table[repo]}, but fleet.yml gives it no ruleset")
        elif repo not in table:
            out.append(f"{repo}: fleet.yml requires {fleet[repo]}, but the table has no row for it")
        elif sorted(table[repo]) != sorted(fleet[repo]):
            out.append(f"{repo}: the table lists {table[repo]}, fleet.yml requires {fleet[repo]}")
    return out


@pytest.fixture
def app_ids(monkeypatch):
    for k, v in APP_IDS.items():
        monkeypatch.setenv(k, v)


# ---------------------------------------------------------------- the tests

def test_the_page_table_matches_the_shipped_fleet(app_ids, tmp_path):
    table = table_rows(PAGE.read_text(encoding="utf-8"))
    fleet = fleet_checks(FLEET.read_text(encoding="utf-8"), FRAGMENT.read_text(encoding="utf-8"), tmp_path)
    assert len(fleet) >= 6, f"the fleet resolved fewer rulesets than the kit's six repos: {sorted(fleet)}"
    diffs = differences(table, fleet)
    assert not diffs, f"{PAGE.relative_to(KIT)} disagrees with {FLEET.relative_to(KIT)}:\n" + "\n".join(diffs)


def test_a_row_that_differs_is_named_with_both_lists(app_ids, tmp_path):
    fleet = (
        "defaults:\n"
        "  ruleset:\n"
        "    enabled: true\n"
        "    name: main\n"
        "    enforcement: active\n"
        "    admin_bypass: always\n"
        "    required_status_checks: [agent-checks]\n"
        "repos:\n"
        "  - name: example-owner/one\n"
        "    manage: [\"all\"]\n"
        "  - name: example-owner/two\n"
        "    manage: [\"all\"]\n"
        "    overrides:\n"
        "      ruleset:\n"
        "        required_status_checks: [test, agent-checks]\n"
        "  - name: example-owner/labels-only\n"
        "    manage: [\"labels\"]\n"
    )
    fragment = (
        "repos:\n"
        "  - name: example-owner/three\n"
        "    manage: [\"all\"]\n"
        "    overrides:\n"
        "      ruleset:\n"
        "        required_status_checks: [unit]\n"
    )
    page = (
        "| Repo | Required checks |\n|---|---|\n"
        "| `one` | `agent-checks` |\n"
        "| `two` | `agent-checks`, `test`, `gone` |\n"
        "| `extra` | `agent-checks` |\n"
    )
    resolved = fleet_checks(fleet, fragment, tmp_path)
    assert resolved == {"one": ["agent-checks"], "two": ["test", "agent-checks"], "three": ["unit"]}
    assert differences(table_rows(page), resolved) == [
        "extra: the table lists ['agent-checks'], but fleet.yml gives it no ruleset",
        "three: fleet.yml requires ['unit'], but the table has no row for it",
        "two: the table lists ['agent-checks', 'test', 'gone'], fleet.yml requires ['test', 'agent-checks']",
    ]


def test_a_check_without_backticks_is_refused():
    page = "| Repo | Required checks |\n|---|---|\n| `one` | `agent-checks`, test |\n"
    with pytest.raises(AssertionError, match="backticks"):
        table_rows(page)
