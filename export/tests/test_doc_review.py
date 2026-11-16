"""doc_review.py: which hand-written pages a re-sync may have made stale.

The re-sync moves starter/ under the pages in docs/, and nothing told the
reviewer which pages describe a changed source. export/doc-sources.yml maps
each page to the starter paths it describes; doc_review.py turns a diff into
a "Pages to review" section for the pull request. These tests pin glob
semantics (`*` must not cross `/`), the map's validation, the rendering, and
the advisory coverage check. No network; the one git test builds a throwaway
repo.
Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import warnings
from pathlib import Path

import pytest
import yaml

EXPORT_DIR = Path(__file__).resolve().parents[1]
KIT_ROOT = EXPORT_DIR.parent
_spec = importlib.util.spec_from_file_location("kit_doc_review", EXPORT_DIR / "doc_review.py")
dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dr)


def put(root: Path, rel: str, text: str = "x\n") -> None:
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")


# -- glob matching ------------------------------------------------------------

@pytest.mark.parametrize("path, glob, expected", [
    ("a/b.md", "a/**", True),
    ("a/b/c/d.md", "a/**", True),
    ("a", "a/**", False),
    ("ab/c.md", "a/**", False),
    ("a/b.md", "a/*.md", True),
    ("a/b/c.md", "a/*.md", False),
    ("a/b.txt", "a/*.md", False),
    ("a/b/c.md", "a/**/c.md", True),
    ("a/c.md", "a/**/c.md", True),
    ("a/x/y/c.md", "a/**/c.md", True),
    ("a/b.md", "a/b.md", True),
    ("a/bxmd", "a/b.md", False),
    ("starter/x/README.md", "starter/*/README.md", True),
    ("starter/x/y/README.md", "starter/*/README.md", False),
    ("a/b1.md", "a/b?.md", True),
    ("a/b/.md", "a/b?.md", False),
])
def test_glob_semantics_keep_star_inside_one_segment(path, glob, expected):
    assert dr.match_glob(path, glob) is expected


# -- map validation -----------------------------------------------------------

@pytest.fixture
def tree(tmp_path):
    put(tmp_path, "docs/one.md", "page one\n")
    put(tmp_path, "starter/r/docs/routines/spec.md")
    put(tmp_path, "starter/r/a.txt")
    return tmp_path


def _check(tree, doc):
    return dr.validate_map(doc, tree)


def test_a_valid_map_passes_and_fills_defaults(tree):
    out = _check(tree, {"pages": {"docs/one.md": ["starter/r/docs/routines/**"]}})
    assert out["required"] is False
    assert out["not_documented"] == []


@pytest.mark.parametrize("doc, needle", [
    ({"pages": {"docs/one.md": ["starter/r/a.txt"]}, "extra": 1}, "extra"),
    ({"pages": {"docs/missing.md": ["starter/r/a.txt"]}}, "docs/missing.md"),
    ({"pages": {"docs/one.md": ["starter/r/nope/**"]}}, "starter/r/nope/**"),
    ({"pages": {"docs/one.md": ["elsewhere/a.txt"]}}, "elsewhere/a.txt"),
    ({"pages": {"docs/one.md": []}}, "docs/one.md"),
    ({"required": "yes", "pages": {"docs/one.md": ["starter/r/a.txt"]}}, "required"),
    ({"pages": {"docs/one.md": ["starter/r/a.txt"]},
      "not_documented": [{"path": "starter/r/a.txt"}]}, "starter/r/a.txt"),
    ({"pages": {"docs/one.md": ["starter/r/a.txt"]},
      "not_documented": [{"path": "starter/r/a.txt", "reason": "  "}]}, "starter/r/a.txt"),
    ({"pages": {"docs/one.md": ["starter/r/a.txt"]},
      "not_documented": [{"path": "starter/r/gone.md", "reason": "why"}]}, "starter/r/gone.md"),
])
def test_a_bad_map_raises_naming_the_entry(tree, doc, needle):
    with pytest.raises(dr.MapError) as exc:
        _check(tree, doc)
    assert needle in str(exc.value)


def test_the_command_line_exits_2_on_a_bad_map(tree, capsys):
    bad = tree / "map.yml"
    bad.write_text(yaml.safe_dump({"pages": {"docs/missing.md": ["starter/r/a.txt"]}}))
    rc = dr.main(["--base", "HEAD", "--root", str(tree), "--map", str(bad)])
    assert rc == 2
    assert "docs/missing.md" in capsys.readouterr().err


# -- rendering ----------------------------------------------------------------

DOC = {"required": False, "not_documented": [],
       "pages": {"docs/one.md": ["starter/r/**"], "docs/two.md": ["starter/s/*.md"]}}


def test_render_orders_added_and_deleted_before_modified_and_omits_untouched_pages():
    changes = [("modified", "starter/r/m.md", None), ("renamed", "starter/r/new.md", "starter/r/old.md"),
               ("deleted", "starter/r/d.md", None), ("added", "starter/r/a.md", None)]
    text = dr.render(changes, DOC, [])
    assert "### docs/one.md" in text and "### docs/two.md" not in text
    lines = [l for l in text.splitlines() if l.startswith("- `starter/r/")]
    assert lines == [
        "- `starter/r/a.md` (added)",
        "- `starter/r/d.md` (deleted)",
        "- `starter/r/m.md` (modified)",
        "- `starter/r/new.md` (renamed from `starter/r/old.md`)",
    ]


def test_a_rename_out_of_a_mapped_path_still_hits_the_page():
    text = dr.render([("renamed", "starter/z/new.md", "starter/r/old.md")], DOC, [])
    assert "### docs/one.md" in text


def test_render_caps_a_pages_list_at_15_lines():
    changes = [("modified", f"starter/r/f{i:02d}.md", None) for i in range(20)]
    text = dr.render(changes, DOC, [])
    page = text.split("### docs/one.md")[1].split("###")[0]
    bullets = [l for l in page.splitlines() if l.startswith("- ")]
    assert len(bullets) == 16
    assert bullets[-1] == "- and 5 more"


def test_render_says_so_when_no_mapped_source_changed():
    text = dr.render([("modified", "starter/other/x.md", None)], DOC, [])
    assert text.startswith("## Pages to review\n")
    assert "No mapped source changed" in text
    assert "### docs/" not in text


def test_new_on_no_page_lists_added_adrs_specs_and_workflows_mapped_or_not():
    changes = [
        ("added", "starter/r/docs/decisions/0001-x.md", None),
        ("added", "starter/r/docs/routines/new.md", None),
        ("added", "starter/r/docs/routine/new.md", None),
        ("added", "starter/r/.github/workflows/new.yml", None),
        ("modified", "starter/r/docs/decisions/0002-y.md", None),
        ("deleted", "starter/r/docs/routines/old.md", None),
        ("added", "starter/r/README.md", None),
    ]
    assert dr.new_on_no_page(changes) == sorted([
        "starter/r/docs/decisions/0001-x.md", "starter/r/docs/routines/new.md",
        "starter/r/docs/routine/new.md", "starter/r/.github/workflows/new.yml"])
    text = dr.render(changes, DOC, [])
    section = text.split("### New, on no page yet")[1].split("### Coverage")[0]
    assert "starter/r/docs/routines/new.md" in section and "README.md" not in section


def test_render_has_a_coverage_subsection():
    text = dr.render([], DOC, ["starter/r/docs/routines/spec.md"])
    assert "### Coverage (advisory)" in text
    assert "- `starter/r/docs/routines/spec.md`" in text.split("### Coverage (advisory)")[1]


def test_parse_name_status_reads_nul_separated_output():
    out = "A\0starter/a.md\0M\0starter/b.md\0R087\0starter/old.md\0starter/new.md\0D\0starter/c.md\0"
    assert dr.parse_name_status(out) == [
        ("added", "starter/a.md", None), ("modified", "starter/b.md", None),
        ("renamed", "starter/new.md", "starter/old.md"), ("deleted", "starter/c.md", None)]


# -- coverage -----------------------------------------------------------------

def _fabricated(tmp_path):
    put(tmp_path, "README.md", "readme names readme-named.md\n")
    put(tmp_path, "bootstrap/README.md", "nothing here\n")
    put(tmp_path, "docs/page.md", "The page names named.md and sched-named.yml.\n")
    put(tmp_path, "starter/r/docs/routines/named.md")
    put(tmp_path, "starter/r/docs/routines/unnamed.md")
    put(tmp_path, "starter/r/docs/routine/readme-named.md")
    put(tmp_path, "starter/r/docs/routines/exempt.md")
    put(tmp_path, "starter/r/docs/routines/notes.txt")
    wf = "starter/r/.github/workflows/"
    put(tmp_path, wf + "sched-named.yml", "on:\n  schedule:\n    - cron: '1 2 * * *'\njobs: {}\n")
    put(tmp_path, wf + "sched-unnamed.yml", "on:\n  workflow_dispatch:\n  schedule:\n    - cron: '1 2 * * *'\njobs: {}\n")
    put(tmp_path, wf + "push-only.yml", "on:\n  push:\n  pull_request:\njobs: {}\n")
    put(tmp_path, wf + "on-list.yml", "on: [push]\njobs: {}\n")
    put(tmp_path, wf + "quoted-on.yml", "'on':\n  schedule:\n    - cron: '1 2 * * *'\njobs: {}\n")
    return tmp_path


def test_undocumented_finds_unnamed_specs_and_scheduled_workflows(tmp_path):
    root = _fabricated(tmp_path)
    doc = {"not_documented": [{"path": "starter/r/docs/routines/exempt.md", "reason": "internal"}]}
    assert dr.undocumented(root, doc) == [
        "starter/r/.github/workflows/quoted-on.yml",
        "starter/r/.github/workflows/sched-unnamed.yml",
        "starter/r/docs/routines/unnamed.md",
    ]


def test_undocumented_reads_the_on_key_whether_pyyaml_makes_it_true_or_a_string(tmp_path):
    root = _fabricated(tmp_path)
    assert yaml.safe_load((root / "starter/r/.github/workflows/sched-named.yml").read_text()).get(True)
    assert "on" in yaml.safe_load((root / "starter/r/.github/workflows/quoted-on.yml").read_text())
    found = dr.undocumented(root, {"not_documented": []})
    assert "starter/r/.github/workflows/quoted-on.yml" in found
    assert "starter/r/.github/workflows/sched-named.yml" not in found


# -- the real map against the real tree ---------------------------------------

def _enforce(findings: list[str], required: bool) -> None:
    """Advisory findings warn (the count shows in pytest's summary); required ones fail."""
    if required and findings:
        pytest.fail("pages do not name: " + ", ".join(findings))
    for path in findings:
        warnings.warn(f"no page names {path}", stacklevel=2)


def test_the_real_map_validates_against_the_real_tree():
    doc = dr.validate_map(dr.load_map(EXPORT_DIR / "doc-sources.yml"), KIT_ROOT)
    pages = {f"docs/{p.name}" for p in (KIT_ROOT / "docs").glob("*.md")}
    assert pages == set(doc["pages"]), "every docs/*.md page needs an entry in export/doc-sources.yml"


def test_the_real_tree_coverage_is_advisory_unless_the_map_says_required():
    doc = dr.validate_map(dr.load_map(EXPORT_DIR / "doc-sources.yml"), KIT_ROOT)
    _enforce(dr.undocumented(KIT_ROOT, doc), doc["required"])


def test_advisory_findings_warn_and_pass(tmp_path):
    findings = dr.undocumented(_fabricated(tmp_path), {"not_documented": []})
    assert findings
    with pytest.warns(UserWarning) as record:
        _enforce(findings, required=False)
    assert len(record) == len(findings)


def test_required_findings_fail(tmp_path):
    findings = dr.undocumented(_fabricated(tmp_path), {"not_documented": []})
    with pytest.raises(pytest.fail.Exception):
        _enforce(findings, required=True)


# -- git ----------------------------------------------------------------------

def _git(root: Path, *args: str) -> None:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", str(root), *args],
                   check=True, capture_output=True, env=env)


def test_git_changes_see_modified_deleted_renamed_and_untracked_files(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    root = tmp_path
    _git(root, "init", "-q")
    put(root, "starter/r/keep.md", "keep\n" * 20)
    put(root, "starter/r/edit.md", "one\n")
    put(root, "starter/r/gone.md", "gone\n")
    put(root, "starter/r/move.md", "moving content\n" * 20)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    put(root, "starter/r/edit.md", "two\n")
    (root / "starter/r/gone.md").unlink()
    _git(root, "mv", "starter/r/move.md", "starter/r/moved.md")
    put(root, "starter/r/fresh.md", "new\n")
    changes = sorted(dr.git_changes(root, "HEAD"))
    assert changes == sorted([
        ("modified", "starter/r/edit.md", None), ("deleted", "starter/r/gone.md", None),
        ("renamed", "starter/r/moved.md", "starter/r/move.md"), ("added", "starter/r/fresh.md", None)])
