"""resync_stale_fix.py: is an open fix pull request behind the held sources' heads?

No network: the held heads and the pull request's manifests are temp files.
Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

EXPORT_DIR = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("kit_resync_stale_fix", EXPORT_DIR / "resync_stale_fix.py")
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)

A, B = "a" * 40, "b" * 40
A_NEW, B_NEW = "1" * 40, "2" * 40


def manifest(repo, sha, extra=""):
    return f"repo: {repo}\nsource: src-{repo}\nsource_sha: {sha}\n{extra}"


@pytest.fixture
def pr(tmp_path):
    d = tmp_path / "pr"
    d.mkdir()
    (d / "a.yml").write_text(manifest("a", A), encoding="utf-8")
    (d / "b.yml").write_text(manifest("b", B), encoding="utf-8")
    (d / "_common.yml").write_text("protect: []\n", encoding="utf-8")
    return d


def held(tmp_path, data):
    path = tmp_path / "held-heads.json"
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return str(path)


def test_fresh_when_the_pr_pins_are_the_held_heads(tmp_path, pr, capsys):
    assert sf.main([held(tmp_path, {"src-a": A, "src-b": B}), str(pr)]) == 0
    assert capsys.readouterr().out == "\n"


def test_stale_for_one_of_two_held_sources(tmp_path, pr, capsys):
    assert sf.main([held(tmp_path, {"src-b": B_NEW, "src-a": A}), str(pr)]) == 0
    assert capsys.readouterr().out == "src-b\n"


def test_stale_for_both_is_sorted_on_one_line(tmp_path, pr, capsys):
    assert sf.main([held(tmp_path, {"src-b": B_NEW, "src-a": A_NEW}), str(pr)]) == 0
    assert capsys.readouterr().out == "src-a src-b\n"


def test_a_missing_manifest_for_a_held_source_exits_2(tmp_path, pr, capsys):
    (pr / "b.yml").unlink()
    assert sf.main([held(tmp_path, {"src-a": A, "src-b": B}), str(pr)]) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and "src-b" in cap.err and len(cap.err.splitlines()) == 1


@pytest.mark.parametrize("data", ["{not json", "[]", "{}", '{"src-a": "short"}', '{"../x": "' + "a" * 40 + '"}'])
def test_a_malformed_held_heads_file_exits_2(tmp_path, pr, capsys, data):
    assert sf.main([held(tmp_path, data), str(pr)]) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and len(cap.err.splitlines()) == 1


def test_a_missing_held_heads_file_exits_2(tmp_path, pr, capsys):
    assert sf.main([str(tmp_path / "nope.json"), str(pr)]) == 2
    assert "nope.json" in capsys.readouterr().err


def test_a_manifest_that_will_not_parse_exits_2_without_printing_it(tmp_path, pr, capsys):
    (pr / "b.yml").write_text("repo: [unclosed SECRET-TEXT\n", encoding="utf-8")
    assert sf.main([held(tmp_path, {"src-a": A}), str(pr)]) == 2
    cap = capsys.readouterr()
    assert "b.yml" in cap.err and "SECRET-TEXT" not in cap.err + cap.out


def test_a_sha_in_another_manifest_for_the_same_source_is_not_confused(tmp_path, pr, capsys):
    # b.yml imports src-a at the held head, but its own source is src-b.
    (pr / "b.yml").write_text(manifest("b", B, f"imports:\n  - repo: src-a\n    sha: {A_NEW}\n    path: x\n"),
                              encoding="utf-8")
    assert sf.main([held(tmp_path, {"src-a": A_NEW}), str(pr)]) == 0
    assert capsys.readouterr().out == "src-a\n"
    # And a src-a import inside src-a's own manifest, pinned apart, does not matter either.
    (pr / "a.yml").write_text(manifest("a", A, f"imports:\n  - repo: src-a\n    sha: {A_NEW}\n    path: x\n"),
                              encoding="utf-8")
    assert sf.main([held(tmp_path, {"src-a": A}), str(pr)]) == 0
    assert capsys.readouterr().out == "\n"
