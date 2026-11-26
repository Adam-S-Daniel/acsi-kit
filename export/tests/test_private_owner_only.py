"""The private registry's starter ships none of its source owner's machinery.

export/patches/agentskills-private/owner_only.py cuts the eval-protection gate,
the left-out workflows' lockfile entries, and the AGENTS.md and README.md text
about what the include list leaves out (DECISIONS "Re-pin of the private
registry (2026-11-26)"). These tests hold the shipped tree to that, reading
each file with its parser, and the patch's cuts to their shape.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

KIT = Path(__file__).resolve().parents[2]
TREE = KIT / "starter/agent-skills-private"
_spec = importlib.util.spec_from_file_location(
    "kit_patch_owner_only", KIT / "export/patches/agentskills-private/owner_only.py")
owner_only = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(owner_only)

def test_the_shipped_tree_has_no_infrastructure_or_plugin_hooks():
    files = [p.relative_to(TREE).as_posix() for p in TREE.rglob("*") if p.is_file()]
    assert not [f for f in files if f.startswith("infrastructure/")]
    assert not [f for f in files if f.startswith("plugins/") and "/hooks/" in f]
    assert not [f for f in files if f.startswith(".github/workflows/") and f.endswith(".yml")
                and f != owner_only.AGENT_CHECKS]


def test_agent_checks_runs_no_other_repos_code():
    doc = yaml.safe_load((TREE / owner_only.AGENT_CHECKS).read_text(encoding="utf-8"))
    job = doc["jobs"]["agent-checks"]
    assert "permissions" not in job        # the workflow's contents: read applies
    for step in job["steps"]:
        assert not (step.get("with") or {}).get("repository"), step
    assert [s.get("name") for s in job["steps"]] == [None, "Verify action lockfile", "Run the commit-time checks over this change"]


def test_the_lockfile_names_only_workflows_in_the_tree_and_the_tags_they_use():
    lock = yaml.safe_load((TREE / owner_only.LOCK).read_text(encoding="utf-8"))
    present = {f".github/workflows/{p.name}" for p in (TREE / ".github/workflows").glob("*.yml")}
    assert set(lock["workflows"]) == present
    used = {u for uses in lock["workflows"].values() for u in (uses or [])}
    assert set(lock["dependencies"]) == used


def test_the_plugin_declares_no_hooks():
    plugin = json.loads((TREE / "plugins/acsi-private-anything-anywhere/.claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert "hooks" not in plugin
    market = json.loads((TREE / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    assert all("records" not in p["description"] for p in market["plugins"])


def test_the_readme_describes_no_hook_the_bundle_does_not_ship():
    text = (TREE / "README.md").read_text(encoding="utf-8")
    assert "Stop hook" not in text and "hooks/claude-code.json" not in text


def test_agents_md_ends_at_the_marker():
    text = (TREE / "AGENTS.md").read_text(encoding="utf-8")
    assert text.rstrip("\n").endswith(owner_only.MARKER)


LOCK_SRC = """\
# head
version: 'v0.0.3'
workflows:
    '.github/workflows/agent-checks.yml':
        - 'actions/checkout@v7.0.1'
    '.github/workflows/gone.yml': []
    '.github/workflows/owner.yml':
        - 'actions/checkout@v7.0.1'
        - 'vendor/only-owner@v1.0.0'
dependencies:
    'actions/checkout@v7.0.1':
        ref: 'v7.0.1'
        commit: 'sha1-0000000000000000000000000000000000000001'
    'vendor/only-owner@v1.0.0':
        ref: 'v1.0.0'
        commit: 'sha1-0000000000000000000000000000000000000002'
"""


def test_the_lock_cut_drops_absent_workflows_and_their_only_tags():
    out = owner_only.cut_lock(LOCK_SRC, {".github/workflows/agent-checks.yml"})
    doc = yaml.safe_load(out)
    assert list(doc["workflows"]) == [".github/workflows/agent-checks.yml"]
    assert list(doc["dependencies"]) == ["actions/checkout@v7.0.1"]
    assert out.startswith("# head\nversion: 'v0.0.3'\n")


GATE_SRC = """\
jobs:
  agent-checks:
    runs-on: ubuntu-latest
""" + owner_only.PERMS + """\
    steps:
      - uses: actions/checkout@v7.0.1
      - name: Run
        run: bash .githooks/agent-checks ci

""" + owner_only.GATE_COMMENT + """ an edit to a skill...
      - name: Check out the eval-protection gate
        uses: actions/checkout@v7.0.1
        with:
          repository: example-adopter/_agent-guidance
"""


def test_the_gate_cut_leaves_the_checks_and_drops_the_gate():
    out = owner_only.cut_gate(GATE_SRC)
    steps = yaml.safe_load(out)["jobs"]["agent-checks"]["steps"]
    assert [s.get("name") for s in steps] == [None, "Run"]
    assert "permissions" not in yaml.safe_load(out)["jobs"]["agent-checks"]


def test_a_step_after_the_gate_stops_the_cut():
    text = GATE_SRC + "      - name: A step the source adds later\n        run: echo later\n"
    with pytest.raises(SystemExit, match="not the gate's"):
        owner_only.cut_gate(text)


def test_the_synced_scanners_are_the_ones_agent_guidance_delivers():
    ag = KIT / "starter/agent-guidance/templates"
    assert (TREE / ".githooks/privacy-denylist.py").read_bytes() == (ag / "agent-checks/privacy-denylist.py").read_bytes()
    assert (TREE / ".githooks/privacy-comment-scan.py").read_bytes() == \
        (ag / "privacy-comment-alert/privacy-comment-scan.py").read_bytes()


@pytest.mark.parametrize("fn, text", [
    (owner_only.cut_gate, "jobs: {}\n"),                         # no gate block
    (owner_only.cut_agents, "# AGENTS.md\n"),                     # no marker
    (owner_only.cut_readme, "# README\nno hooks paragraph\n"),    # no hooks paragraphs
])
def test_a_cut_that_does_not_find_its_shape_stops_the_export(fn, text):
    with pytest.raises(SystemExit):
        fn(text)
