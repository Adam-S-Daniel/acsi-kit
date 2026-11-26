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
