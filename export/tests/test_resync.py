"""resync.py: moving each manifest's pins to its source's head, in place.

No network: every test passes its own ls-remote function.
Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

EXPORT_DIR = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("kit_resync", EXPORT_DIR / "resync.py")
resync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resync)

OLD, OTHER, NEW, PLATFORM = "a" * 40, "b" * 40, "c" * 40, "d" * 40

ONE = f"""\
# A comment the rewrite must keep.
repo: one
kit_name: one-kit
source: src-one
source_sha: {OLD}   # trailing comment

imports:
  - repo: platform
    sha: {PLATFORM}
    path: x
  - repo: src-one
    sha: '{OLD}'
    path: y
edits:
  - path: z
    old: "pin {OLD}\\n"
    new: "pin {OLD}\\n"
"""

TWO = f"""\
repo: two
source_sha: {OTHER}
"""

PRIVATE = f"""\
repo: agentskills-private
source: secret-src
source_sha: {OTHER}
"""


@pytest.fixture
def manifests(tmp_path):
    d = tmp_path / "manifests"
    d.mkdir()
    (d / "one.yml").write_text(ONE, encoding="utf-8")
    (d / "two.yml").write_text(TWO, encoding="utf-8")
    (d / "agentskills-private.yml").write_text(PRIVATE, encoding="utf-8")
    (d / "_common.yml").write_text("protect: []\n", encoding="utf-8")
    return d


def heads(table):
    calls = []

    def ls_remote(owner, repo):
        calls.append((owner, repo))
        return table[repo]
    return ls_remote, calls


def test_moves_the_source_sha_and_same_repo_imports_and_nothing_else(manifests):
    ls, calls = heads({"src-one": NEW, "two": OTHER})
    got = resync.resync(manifests, "example-owner", ls)
    assert got == [("src-one", OLD, NEW), ("two", OTHER, OTHER)]
    assert sorted(calls) == [("example-owner", "src-one"), ("example-owner", "two")]
    text = (manifests / "one.yml").read_text(encoding="utf-8")
    # Only the two pins moved: comments, quotes, the other repo's import and
    # the same sha inside an edit's text are untouched.
    assert text == ONE.replace(f"source_sha: {OLD}", f"source_sha: {NEW}").replace(f"sha: '{OLD}'", f"sha: '{NEW}'")
    doc = yaml.safe_load(text)
    assert doc["source_sha"] == NEW
    assert [i["sha"] for i in doc["imports"]] == [PLATFORM, NEW]


def test_skips_the_private_manifest_and_never_asks_for_it(manifests):
    ls, calls = heads({"src-one": NEW, "two": NEW})
    resync.resync(manifests, "example-owner", ls)
    assert ("example-owner", "secret-src") not in calls
    assert (manifests / "agentskills-private.yml").read_text(encoding="utf-8") == PRIVATE


def test_unchanged_leaves_the_files_byte_for_byte(manifests):
    ls, _ = heads({"src-one": OLD, "two": OTHER})
    got = resync.resync(manifests, "example-owner", ls)
    assert all(old == new for _, old, new in got)
    assert (manifests / "one.yml").read_text(encoding="utf-8") == ONE
    assert (manifests / "two.yml").read_text(encoding="utf-8") == TWO


def test_a_bad_head_writes_nothing(manifests):
    ls, _ = heads({"src-one": NEW, "two": "not-a-sha"})
    with pytest.raises(resync.ResyncError, match="not a full sha"):
        resync.resync(manifests, "example-owner", ls)
    assert (manifests / "one.yml").read_text(encoding="utf-8") == ONE


def test_refuses_a_bad_owner_an_unsafe_source_and_an_unknown_skip(manifests):
    ls, _ = heads({})
    with pytest.raises(resync.ResyncError, match="not a GitHub owner"):
        resync.resync(manifests, "bad/owner", ls)
    with pytest.raises(resync.ResyncError, match="no manifest for nope"):
        resync.resync(manifests, "example-owner", ls, skip=("nope",))
    (manifests / "two.yml").write_text(f"repo: two\nsource: ../x\nsource_sha: {OTHER}\n", encoding="utf-8")
    with pytest.raises(resync.ResyncError, match="unsafe source repo name"):
        resync.resync(manifests, "example-owner", ls)


def test_refuses_a_short_pinned_sha(manifests):
    (manifests / "two.yml").write_text("repo: two\nsource_sha: abc123\n", encoding="utf-8")
    with pytest.raises(resync.ResyncError, match="not a full sha"):
        resync.resync(manifests, "example-owner", heads({})[0])


def test_main_prints_one_line_per_source_and_writes_the_summary(manifests, tmp_path, capsys):
    ls, _ = heads({"src-one": NEW, "two": OTHER})
    summary = tmp_path / "summary.md"
    rc = resync.main(["--owner", "example-owner", "--manifests", str(manifests), "--summary", str(summary)], ls_remote=ls)
    assert rc == 0
    assert capsys.readouterr().out.splitlines() == [f"src-one: {OLD[:12]} -> {NEW[:12]}", "two: unchanged"]
    md = summary.read_text(encoding="utf-8")
    assert f"https://github.com/example-owner/src-one/compare/{OLD}...{NEW}" in md
    assert "| `two` |" in md and "unchanged" in md


def test_the_real_manifests_all_parse_and_name_a_full_sha():
    for path in sorted((EXPORT_DIR / "manifests").glob("*.yml")):
        if path.name == "_common.yml":
            continue
        key, source, spans = resync.sha_spans(path.read_text(encoding="utf-8"), path.name)
        assert spans and all(resync.SHA.fullmatch(s) for _, _, s in spans), path.name
