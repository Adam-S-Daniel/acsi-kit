"""resync_holdback.py: hold back the source whose new head breaks the kit.

No network, no git, no export: a fake runner decides which pins pass.
Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

EXPORT_DIR = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("kit_resync_holdback", EXPORT_DIR / "resync_holdback.py")
hb = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = hb  # dataclasses looks its module up
_spec.loader.exec_module(hb)

OLD_A, NEW_A = "a" * 40, "1" * 39 + "e"
OLD_B, NEW_B = "b" * 40, "2" * 39 + "e"
OLD_C, NEW_C = "c" * 40, "3" * 39 + "e"
LIB_PIN = "d" * 40
OWNER = "example-owner"


def manifest(repo, sha, extra=""):
    return f"# keep me\nrepo: {repo}\nsource: src-{repo}\nsource_sha: {sha}   # trailing\n{extra}"


A_EXTRA = f"""imports:
  - repo: lib
    sha: {LIB_PIN}
    path: x
  - repo: src-a
    sha: '{{old}}'
    path: y
"""


def texts(a, b, c):
    return {
        "a.yml": manifest("a", a, A_EXTRA.replace("{old}", a)),
        "b.yml": manifest("b", b),
        "c.yml": manifest("c", c),
    }


OLD_TEXTS = texts(OLD_A, OLD_B, OLD_C)
NEW_TEXTS = texts(NEW_A, NEW_B, NEW_C)


class FakeRunner:
    """Passes unless the manifests on disk hold a bad pin, or the set of bad combos."""

    def __init__(self, manifests, bad_pins=(), bad_combos=()):
        self.manifests, self.bad_pins, self.bad_combos = manifests, set(bad_pins), [set(c) for c in bad_combos]
        self.states, self.resets = [], 0

    def pins(self):
        return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8"))["source_sha"]
                for p in self.manifests.glob("*.yml")}

    def run(self):
        pins = self.pins()
        self.states.append(pins)
        bad = [n for n, sha in pins.items() if sha in self.bad_pins]
        if bad:
            return False, "line\n" * 50 + f"FAILED anchor in {bad[0]} SECRET-LOG-TEXT"
        moved = {n for n, sha in pins.items() if sha != {"a": OLD_A, "b": OLD_B, "c": OLD_C}[n]}
        if any(c <= moved for c in self.bad_combos):
            return False, "combination failed SECRET-LOG-TEXT"
        return True, "ok"

    def reset(self):
        self.resets += 1


@pytest.fixture
def manifests(tmp_path):
    d = tmp_path / "manifests"
    d.mkdir()
    for name, text in NEW_TEXTS.items():
        (d / name).write_text(text, encoding="utf-8")
    return d


def on_disk(d):
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(d.glob("*.yml"))}


def test_everything_passes_so_nothing_is_held_back(manifests):
    runner = FakeRunner(manifests)
    result = hb.holdback(manifests, OLD_TEXTS, runner)
    assert result.held == {} and not result.all_held and not result.interaction
    assert on_disk(manifests) == NEW_TEXTS
    assert len(runner.states) == 1


def test_nothing_moved_runs_nothing(manifests):
    for name, text in OLD_TEXTS.items():
        (manifests / name).write_text(text, encoding="utf-8")
    runner = FakeRunner(manifests)
    result = hb.holdback(manifests, OLD_TEXTS, runner)
    assert result.moved == {} and runner.states == []


def test_one_source_breaking_alone_is_held_and_the_others_move(manifests):
    runner = FakeRunner(manifests, bad_pins={NEW_B})
    result = hb.holdback(manifests, OLD_TEXTS, runner)
    assert sorted(result.held) == ["src-b"] and not result.all_held and not result.interaction
    assert on_disk(manifests) == {"a.yml": NEW_TEXTS["a.yml"], "b.yml": OLD_TEXTS["b.yml"], "c.yml": NEW_TEXTS["c.yml"]}
    # full set, then each alone, then the two that passed together.
    assert len(runner.states) == 5
    assert runner.states[-1] == {"a": NEW_A, "b": OLD_B, "c": NEW_C}
    assert runner.resets == 0


def test_two_sources_breaking_are_both_held(manifests):
    runner = FakeRunner(manifests, bad_pins={NEW_A, NEW_C})
    result = hb.holdback(manifests, OLD_TEXTS, runner)
    assert sorted(result.held) == ["src-a", "src-c"]
    assert on_disk(manifests) == {"a.yml": OLD_TEXTS["a.yml"], "b.yml": NEW_TEXTS["b.yml"], "c.yml": OLD_TEXTS["c.yml"]}


def test_each_passes_alone_but_the_combination_fails_so_all_are_held(manifests):
    runner = FakeRunner(manifests, bad_combos=[{"a", "b"}])
    result = hb.holdback(manifests, OLD_TEXTS, runner)
    assert result.interaction and result.all_held
    assert sorted(result.held) == ["src-a", "src-b", "src-c"]
    assert on_disk(manifests) == OLD_TEXTS
    assert runner.resets == 1


def test_a_combination_failing_only_after_the_culprit_is_dropped_holds_everything(manifests):
    # c fails alone; a and b pass alone but fail together.
    runner = FakeRunner(manifests, bad_pins={NEW_C}, bad_combos=[{"a", "b"}])
    result = hb.holdback(manifests, OLD_TEXTS, runner)
    assert result.interaction and result.all_held
    assert on_disk(manifests) == OLD_TEXTS


def test_every_source_failing_alone_holds_all_without_an_interaction(manifests):
    runner = FakeRunner(manifests, bad_pins={NEW_A, NEW_B, NEW_C})
    result = hb.holdback(manifests, OLD_TEXTS, runner)
    assert result.all_held and not result.interaction
    assert on_disk(manifests) == OLD_TEXTS and runner.resets == 1


def test_restoring_a_pin_is_byte_exact_and_moves_only_that_pins_text():
    new = NEW_TEXTS["a.yml"]
    got = hb.restore_pins(new, OLD_TEXTS["a.yml"], "a.yml")
    assert got == OLD_TEXTS["a.yml"]
    assert LIB_PIN in got and "# keep me" in got and "# trailing" in got and f"'{OLD_A}'" in got


def test_restoring_keeps_an_import_that_was_pinned_apart_from_the_source_sha():
    old = manifest("a", OLD_A, f"imports:\n  - repo: src-a\n    sha: {OLD_B}\n    path: y\n")
    new = manifest("a", NEW_A, f"imports:\n  - repo: src-a\n    sha: {NEW_A}\n    path: y\n")
    assert hb.restore_pins(new, old, "a.yml") == old


def run_main(manifests, tmp_path, monkeypatch, runner, tails=True):
    out = tmp_path / "gh-output"
    summary = tmp_path / "summary.md"
    summary.write_text("| Repo | Old | New | Compare |\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    argv = ["--sources", str(tmp_path), "--owner", OWNER, "--manifests", str(manifests), "--summary", str(summary)]
    if tails:
        argv += ["--tails", str(tmp_path / "tails.txt")]
    rc = hb.main(argv, runner=runner, read_old=lambda *_: OLD_TEXTS)
    return rc, out.read_text(encoding="utf-8"), summary.read_text(encoding="utf-8")


def test_main_reports_a_held_source_in_the_outputs_summary_and_tails(manifests, tmp_path, monkeypatch):
    rc, out, md = run_main(manifests, tmp_path, monkeypatch, FakeRunner(manifests, bad_pins={NEW_B}))
    assert rc == 0
    assert out.splitlines() == ["held_back=src-b", "all_held=false"]
    assert md.startswith("| Repo | Old |")          # appended, not replaced
    assert "## Held back" in md and "`src-b`" in md and f"`{OLD_B[:12]}`" in md and f"`{NEW_B[:12]}`" in md
    assert f"https://github.com/{OWNER}/src-b/compare/{OLD_B}...{NEW_B}" in md
    assert "fix routine or a maintainer must follow" in md
    assert "src-a" not in md and "src-c" not in md
    tails = (tmp_path / "tails.txt").read_text(encoding="utf-8")
    assert tails.startswith("== src-b ==\n") and "SECRET-LOG-TEXT" in tails
    # The log text never reaches the summary.
    assert "SECRET-LOG-TEXT" not in md and "FAILED anchor" not in md


def test_main_all_held_sets_the_output_and_names_the_interaction(manifests, tmp_path, monkeypatch):
    rc, out, md = run_main(manifests, tmp_path, monkeypatch, FakeRunner(manifests, bad_combos=[{"a", "b"}]))
    assert rc == 0
    assert out.splitlines() == ["held_back=src-a src-b src-c", "all_held=true"]
    assert "passed alone, but the new heads together break" in md
    assert "SECRET-LOG-TEXT" not in md and (tmp_path / "tails.txt").exists()


def test_main_with_nothing_held_writes_empty_outputs_and_no_section_or_tails(manifests, tmp_path, monkeypatch):
    rc, out, md = run_main(manifests, tmp_path, monkeypatch, FakeRunner(manifests))
    assert rc == 0 and out.splitlines() == ["held_back=", "all_held=false"]
    assert "Held back" not in md and not (tmp_path / "tails.txt").exists()


def test_main_rejects_a_bad_owner(manifests, tmp_path):
    assert hb.main(["--sources", str(tmp_path), "--owner", "bad/owner", "--manifests", str(manifests)]) == 2


def test_the_tail_keeps_the_last_forty_lines():
    text = "\n".join(str(i) for i in range(100))
    assert hb.tail(text).splitlines() == [str(i) for i in range(60, 100)]
