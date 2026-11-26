"""patches/_agent-guidance/kit_only.py: the kit-only merge rule and key do not ship.

Invented trees only. Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

EXPORT_DIR = Path(__file__).resolve().parents[1]
KIT = EXPORT_DIR.parent
_spec = importlib.util.spec_from_file_location(
    "kit_patch_kit_only", EXPORT_DIR / "patches" / "_agent-guidance" / "kit_only.py")
kit_only = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kit_only)

B, E = kit_only.BEGIN, kit_only.END
SPEC = "docs/routines/fleet-worker.md"


def tree(tmp_path: Path, spec: str | None = None, repos: str | None = None) -> Path:
    if spec is not None:
        (tmp_path / SPEC).parent.mkdir(parents=True)
        (tmp_path / SPEC).write_text(spec, encoding="utf-8")
    if repos is not None:
        (tmp_path / "repos.yml").write_text(repos, encoding="utf-8")
    return tmp_path


def run(root: Path) -> None:
    kit_only.apply(root, {})


def test_block_removed_rest_identical(tmp_path):
    root = tree(tmp_path, f"# T\n\nBefore.\n\n{B}\nRule one.\n\nRule two.\n{E}\n\nAfter.\n")
    run(root)
    assert (root / SPEC).read_text() == "# T\n\nBefore.\n\nAfter.\n"


def test_two_blocks(tmp_path):
    root = tree(tmp_path, f"A\n\n{B}\nx\n{E}\n\nB\n\n{B}\ny\n{E}\n\nC\n")
    run(root)
    assert (root / SPEC).read_text() == "A\n\nB\n\nC\n"


def test_block_at_end_of_file(tmp_path):
    root = tree(tmp_path, f"A\n\n{B}\nx\n{E}\n")
    run(root)
    assert (root / SPEC).read_text() == "A\n\n"


def test_no_markers_unchanged(tmp_path):
    text = "# T\r\n\nplain\n\n\n  trailing  "
    root = tree(tmp_path, text)
    (root / SPEC).write_bytes(text.encode())
    run(root)
    assert (root / SPEC).read_bytes() == text.encode()


@pytest.mark.parametrize("text", [
    f"a\n{B}\nx\n",
    f"a\n{E}\nx\n",
    f"a\n{B}\n{B}\nx\n{E}\n{E}\n",
    f"a\n{E}\nx\n{B}\n",
])
def test_bad_markers_name_the_file(tmp_path, text):
    root = tree(tmp_path, text)
    with pytest.raises(SystemExit, match="docs/routines/fleet-worker.md"):
        run(root)
    assert (root / SPEC).read_text() == text


REPOS = """\
# header comment
skills_bootstrap:
  repos:
    - one

# why the resync key exists
# second comment line
kit_resync:
  repo: example-org/kit
  app_slug: example-app

# about the next key
cron_coverage:
  fleet:
    - one
"""


def test_key_and_comment_removed(tmp_path):
    root = tree(tmp_path, repos=REPOS)
    run(root)
    got = (root / "repos.yml").read_text()
    assert got == REPOS.replace(
        "# why the resync key exists\n# second comment line\nkit_resync:\n"
        "  repo: example-org/kit\n  app_slug: example-app\n\n", "")
    assert "kit_resync" not in yaml.safe_load(got)


def test_key_last_in_file(tmp_path):
    root = tree(tmp_path, repos="a: 1\n\n# c\nkit_resync:\n  repo: x\n")
    run(root)
    assert (root / "repos.yml").read_text() == "a: 1\n"


def test_no_key_unchanged(tmp_path):
    text = "# c\na: 1\n\n# d\nb:\n  - 2\n"
    root = tree(tmp_path, repos=text)
    run(root)
    assert (root / "repos.yml").read_text() == text


def test_shipped_fleet_worker_has_no_kit_only_rule():
    text = (KIT / "starter/agent-guidance" / SPEC).read_text(encoding="utf-8")
    assert "kit-only:" not in text
    assert "resync/auto" not in text
    assert "resync-fix/" not in text


def test_shipped_repos_yml_has_no_kit_resync():
    doc = yaml.safe_load((KIT / "starter/agent-guidance/repos.yml").read_text(encoding="utf-8"))
    assert "kit_resync" not in doc


# ── ADR 0051, its index row, the 0041 sentence, and the sweep test ──────────

ADR_PATH = "docs/decisions/" + kit_only.ADR
STATUS = ("**Status:** Accepted. Widens [0028](0028-x.md). Widened by [0045](0045-y.md) (2026-11-15): "
          "more PRs merge too. Widened by [0051](" + kit_only.ADR + ") (2026-11-25): the kit's re-sync "
          "pull requests, opened by an App, merge behind the same review.\n")
INDEX = ("| ADR | Title |\n|---|---|\n| [0050](0050-z.md) | Something |\n"
         "| [0051](" + kit_only.ADR + ") | The fleet worker merges the kit's re-sync pull requests |\n\n## Format\n")
SWEEP = """\
const mutations = {
  oldestfirst: [worker, '**The oldest candidate is taken first**', '**Any candidate may be taken first**'],
  kitauthor: [worker, "Its author's login", 'Its author may be anyone.'],
  kitconfig: [worker, 'merge nothing under this block', 'merge them anyway'],
  kitprivate: [worker, 'It changes neither', 'It may change'],
  kitpins: [worker, 'A sha that is not on the', 'A sha need not be on the'],
  kitmarker: [worker, '<!-- kit-only:end -->\\n', ''],
  argv: ['x.yml', 'a', 'b'],
};

test('fleet worker merges reviewed agent-made changes (ADR 0041)', () => {
  includes(read(worker), ['a']);
});

""" + kit_only.TEST_TITLE + """\
  const text = read(worker);
  assert.ok(text.includes('<!-- kit-only:begin -->'));
  const kit = YAML.parse(read('repos.yml')).kit_resync;
  const adr51 = 'docs/decisions/""" + kit_only.ADR + """';
  includes(read(index), ['| [0051]']);
});

test('fleet worker removes skills the eval verdict retires (ADR 0044)', () => {
  includes(read(worker), ['b']);
});
"""
RUN_TESTS = """\
test_other() {
    if [[ "$rc" -eq 0 && "$pass_n" == "24" ]]; then pass "other: 24 passed"; fi
}

test_prompt_audit_sweep() {
    if [[ "$rc" -eq 0 && "$pass_n" == "24" && "$fail_n" == "0" ]]; then
        pass "prompt-audit sweep policy: 24 passed"
    else
        fail "prompt-audit sweep policy: exit $rc, pass=${pass_n:-?}, fail=${fail_n:-?} (need rc=0, pass=24, fail=0): x"
    fi
}
"""


def full_tree(tmp_path: Path) -> Path:
    files = {ADR_PATH: "# 0051\n", "docs/decisions/README.md": INDEX,
             kit_only.ADR_0041: "# 0041\n\n" + STATUS + "\n## Context\n",
             kit_only.SWEEP_TEST: SWEEP, kit_only.RUN_TESTS: RUN_TESTS}
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    return tmp_path


def test_adr_row_sentence_and_test_cut(tmp_path):
    root = full_tree(tmp_path)
    run(root)
    assert not (root / ADR_PATH).exists()
    assert (root / "docs/decisions/README.md").read_text() == INDEX.replace(
        "| [0051](" + kit_only.ADR + ") | The fleet worker merges the kit's re-sync pull requests |\n", "")
    assert (root / kit_only.ADR_0041).read_text() == (
        "# 0041\n\n**Status:** Accepted. Widens [0028](0028-x.md). Widened by [0045](0045-y.md) (2026-11-15): "
        "more PRs merge too.\n\n## Context\n")
    sweep = (root / kit_only.SWEEP_TEST).read_text()
    assert "ADR 0051" not in sweep and "kit" not in sweep
    assert "(ADR 0041)" in sweep and "(ADR 0044)" in sweep
    assert "oldestfirst:" in sweep and "argv:" in sweep
    assert "});\n\ntest('fleet worker removes skills" in sweep
    assert (root / kit_only.RUN_TESTS).read_text() == RUN_TESTS.replace(
        '"$pass_n" == "24" && "$fail_n"', '"$pass_n" == "23" && "$fail_n"').replace(
        "policy: 24 passed", "policy: 23 passed").replace("pass=24, fail=0", "pass=23, fail=0")


def test_without_adr_and_test_unchanged(tmp_path):
    root = full_tree(tmp_path)
    (root / ADR_PATH).unlink()
    status = STATUS.split(" Widened by [0051]")[0] + "\n"
    (root / kit_only.ADR_0041).write_text(status)
    index = INDEX.replace("| [0051](" + kit_only.ADR + ") | The fleet worker merges the kit's re-sync pull requests |\n", "")
    (root / "docs/decisions/README.md").write_text(index)
    sweep = SWEEP.split(kit_only.TEST_TITLE)[0] + "test('other', () => {});\n"
    (root / kit_only.SWEEP_TEST).write_text(sweep)
    run(root)
    assert (root / kit_only.ADR_0041).read_text() == status
    assert (root / "docs/decisions/README.md").read_text() == index
    assert (root / kit_only.SWEEP_TEST).read_text() == sweep
    assert (root / kit_only.RUN_TESTS).read_text() == RUN_TESTS


def test_adr_named_elsewhere_stops_the_export(tmp_path):
    root = full_tree(tmp_path)
    (root / "docs/other.md").write_text("see [0051](decisions/" + kit_only.ADR + ")\n")
    with pytest.raises(SystemExit, match="still named in: docs/other.md"):
        run(root)


def test_count_stated_twice_stops_the_export(tmp_path):
    root = full_tree(tmp_path)
    text = RUN_TESTS.replace('pass "prompt-audit', 'if [[ "$pass_n" == "24" ]]; then :; fi; pass "prompt-audit')
    (root / kit_only.RUN_TESTS).write_text(text)
    with pytest.raises(SystemExit, match="states its pass count 2 times"):
        run(root)


def test_shipped_tree_has_no_adr_0051_or_its_test():
    ship = KIT / "starter/agent-guidance"
    assert not (ship / ADR_PATH).exists()
    for rel in ("docs/decisions/README.md", kit_only.ADR_0041, kit_only.SWEEP_TEST):
        assert kit_only.ADR not in (ship / rel).read_text(encoding="utf-8"), rel
    sweep = (ship / kit_only.SWEEP_TEST).read_text(encoding="utf-8")
    assert "ADR 0051" not in sweep
    for key in kit_only.KIT_MUTATIONS:
        assert f"{key}:" not in sweep
