"""The places an adopter's repos name a commit of their _agent-guidance.

`bootstrap/regenerate.sh` (run-health-sha, codex-pin) rewrites three of
them after adoption with `bootstrap/lib/guidance_pins.py`. These tests run
the same locators over the kit's own starter trees, so a source change that
moves or reshapes one fails here, at re-sync time, and not on an adopter's
machine: exactly one step named for the eval-protection gate with a 40-hex
ref of the invented owner's _agent-guidance, and exactly one of each pin
line. The rest hold the locators themselves on invented files: what they
refuse, and that a rewrite touches only its own line.

Run: python3 -m pytest export/tests/test_guidance_pins.py -q
"""

import hashlib
import importlib.util
import re
from pathlib import Path

import pytest
import yaml

KIT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("guidance_pins", KIT / "bootstrap/lib/guidance_pins.py")
pins = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pins)

OWNER = "example-adopter"   # the invented owner every starter tree is written for
REGISTRY = KIT / "starter/agent-skills"
SETUP = REGISTRY / "scripts/cloud-env-setup.sh"
CI = REGISTRY / ".github/workflows/ci.yml"
CODEX = KIT / "starter/wsl-automation/scripts/sync-codex-cloud-environments.sh"
INSTALLER = KIT / "starter/agent-guidance/.claude/hooks/fleet-memory.sh"

A, B = "a" * 40, "b" * 40


def read(path):
    return path.read_bytes().decode("utf-8")


# ---------------------------------------------------------------- the real trees

def test_the_registry_starter_has_one_fleet_pin_of_each_kind():
    commit, digest = pins.setup_read(read(SETUP))
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_the_registry_starter_records_the_digest_of_the_guidance_starters_installer():
    # regenerate.sh refuses when the adopter's two copies differ; the kit's
    # own two trees must agree first, or every adopter would be refused.
    _, digest = pins.setup_read(read(SETUP))
    assert digest == hashlib.sha256(INSTALLER.read_bytes()).hexdigest()


def test_the_registry_starter_has_one_gate_step_with_a_full_ref_of_the_owners_guidance():
    assert re.fullmatch(r"[0-9a-f]{40}", pins.gate_read(read(CI), OWNER))


def test_the_gate_rewrite_on_the_real_workflow_changes_one_line():
    before = read(CI)
    after = pins.gate_set(before, OWNER, A)
    changed = [(x, y) for x, y in zip(before.split("\n"), after.split("\n")) if x != y]
    assert len(before.split("\n")) == len(after.split("\n"))
    assert len(changed) == 1 and changed[0][1].strip() == f"ref: {A}"
    assert pins.gate_read(after, OWNER) == A


def test_the_codex_starter_has_one_fleet_pin_of_each_kind_still_the_placeholder():
    commit, digest = pins.codex_read(read(CODEX))
    # The manifest writes ones; regenerate.sh codex-pin reads all ones as "not set yet".
    assert commit == "1" * 40 and digest == "1" * 64


# ---------------------------------------------------------------- invented files

def workflow(*steps):
    return yaml.safe_dump({"name": "CI", "on": {"pull_request": None},
                           "jobs": {"test": {"runs-on": "ubuntu-latest", "steps": list(steps)}}}, sort_keys=False)


def gate(ref=A, repo=f"{OWNER}/_agent-guidance", name=pins.GATE_STEP):
    return {"name": name, "uses": "actions/checkout@v7.0.1", "with": {"repository": repo, "ref": ref, "path": "gate"}}


def test_the_gate_rewrite_leaves_the_same_commit_in_another_step_alone():
    text = workflow(gate(name="Another checkout of the same commit"), gate(), {"run": f"echo {A}"})
    after = yaml.safe_load(pins.gate_set(text, OWNER, B))
    steps = after["jobs"]["test"]["steps"]
    assert [s.get("with", {}).get("ref") for s in steps] == [A, B, None]
    assert steps[2]["run"] == f"echo {A}"


@pytest.mark.parametrize("steps, said", [
    ([], "has 0 step(s)"),
    ([gate(name="Check out the gate")], "has 0 step(s)"),
    ([gate(), gate(ref=B)], "has 2 step(s)"),
    ([gate(repo="someone-else/_agent-guidance")], "checks out someone-else/_agent-guidance"),
    ([gate(repo=f"{OWNER}/skills-evals")], f"want {OWNER}/_agent-guidance"),
    ([gate(ref="main")], "no with.ref of 40 hex"),
    ([gate(ref=A[:39])], "no with.ref of 40 hex"),
    ([{"name": pins.GATE_STEP, "uses": "actions/checkout@v7.0.1"}], "checks out nothing"),
])
def test_a_gate_step_of_the_wrong_shape_is_an_error(steps, said):
    for call in (lambda t: pins.gate_read(t, OWNER), lambda t: pins.gate_set(t, OWNER, B)):
        with pytest.raises(pins.ShapeError) as e:
            call(workflow(*steps))
        assert said in str(e.value)


def test_a_quoted_gate_ref_is_refused_not_half_rewritten():
    text = workflow(gate()).replace(f"ref: {A}", f'ref: "{A}"')
    assert yaml.safe_load(text)["jobs"]["test"]["steps"][0]["with"]["ref"] == A
    with pytest.raises(pins.ShapeError):
        pins.gate_read(text, OWNER)


def test_a_workflow_that_is_not_yaml_is_an_error():
    with pytest.raises(pins.ShapeError):
        pins.gate_read("jobs: [\n", OWNER)


# A hand-written workflow, so the cases below can use YAML that safe_dump never writes.
RAW = f"""name: CI
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Another checkout of the same commit
        uses: actions/checkout@v7.0.1
        with:
          repository: {OWNER}/_agent-guidance
          ref: {A}
      - name: {pins.GATE_STEP}
        uses: actions/checkout@v7.0.1
        with:
          repository: {OWNER}/_agent-guidance
          ref: {A}
          path: gate
"""
GATE_WITH = f"""        with:
          repository: {OWNER}/_agent-guidance
          ref: {A}
          path: gate
"""


def refs(text):
    return [s["with"]["ref"] for s in yaml.safe_load(text)["jobs"]["test"]["steps"]]


def both_refuse(text, said):
    """gate_read and gate_set refuse alike, so a caller learns before it writes anything."""
    for call in (lambda: pins.gate_read(text, OWNER), lambda: pins.gate_set(text, OWNER, B)):
        with pytest.raises(pins.ShapeError) as e:
            call()
        assert said in str(e.value)


def test_the_hand_written_workflow_is_rewritten_in_the_gate_step_only():
    assert RAW.count(GATE_WITH) == 1 and pins.gate_read(RAW, OWNER) == A
    assert refs(pins.gate_set(RAW, OWNER, B)) == [A, B]


def test_a_rewrite_that_changes_how_the_document_parses_is_refused_by_the_proof_alone():
    # Every shape check passes: the file is fine and the commit is 40 hex
    # characters. But YAML reads a plain all-digit value as a number, so the
    # parsed document would differ in more than the text of the ref. Only the
    # comparison of the parsed documents catches it.
    digits = "1" * 40
    assert pins.SHA40.fullmatch(digits) and isinstance(yaml.safe_load(digits), int)
    with pytest.raises(pins.ShapeError) as e:
        pins.gate_set(RAW, OWNER, digits)
    assert "would change something else" in str(e.value)


def test_the_dry_run_command_refuses_what_the_write_would(tmp_path, capsys):
    f = tmp_path / "ci.yml"
    f.write_text(RAW, encoding="utf-8")
    assert pins.main(["gate-try", str(f), "label", OWNER, "1" * 40]) == 2
    assert capsys.readouterr().err.startswith("ERROR: label: the rewrite of the gate step's ref would change something else")
    assert pins.main(["gate-try", str(f), "label", OWNER, B]) == 0
    assert f.read_text(encoding="utf-8") == RAW          # a dry run writes nothing


def test_crlf_line_endings_are_kept():
    crlf = RAW.replace("\n", "\r\n")
    after = pins.gate_set(crlf, OWNER, B)
    assert after == crlf.replace(f"ref: {A}\r\n          path", f"ref: {B}\r\n          path")
    assert after.count("\r\n") == crlf.count("\r\n") and refs(after) == [A, B]


def test_a_flow_style_with_is_rewritten_in_place():
    flow = RAW.replace(GATE_WITH, f"        with: {{repository: {OWNER}/_agent-guidance, ref: {A}, path: gate}}\n")
    after = pins.gate_set(flow, OWNER, B)
    assert f"ref: {B}, path: gate}}" in after and refs(after) == [A, B]


@pytest.mark.parametrize("name, text", [
    # The gate step's `with` is an alias of another step's: the position the
    # parser gives is in that other step.
    ("alias in the gate step", RAW.replace("        with:\n          repository", "        with: &w\n          repository", 1)
                                  .replace(GATE_WITH, "        with: *w\n")),
    # The gate step's own `with` is the anchor, and another step borrows it.
    ("anchor in the gate step", RAW.replace(GATE_WITH, GATE_WITH.replace("with:", "with: &w"))
                                   + "      - name: A later step that borrows it\n        uses: actions/checkout@v7.0.1\n        with: *w\n"),
    ("an anchored ref", RAW.replace(f"ref: {A}\n          path", f"ref: &r {A}\n          path")),
    ("a merge key", RAW.replace("          path: gate\n", "          path: gate\n          <<: {fetch-depth: 1}\n")),
])
def test_a_gate_step_that_shares_yaml_with_another_is_refused(name, text):
    yaml.safe_load(text)                                    # each is valid YAML: the refusal is ours
    both_refuse(text, "uses a YAML anchor, alias or merge key")


def test_the_alias_case_would_have_rewritten_the_other_step():
    # What the refusal prevents, shown on the text itself: the only `ref:` in
    # the file is the other step's.
    text = (RAW.replace("        with:\n          repository", "        with: &w\n          repository", 1)
               .replace(GATE_WITH, "        with: *w\n"))
    assert text.count(f"ref: {A}") == 1 and refs(text) == [A, A]


@pytest.mark.parametrize("text, said", [
    (RAW.replace("          path: gate\n", f"          path: gate\n          ref: {B}\n"), "writes a key of its `with` twice: ref"),
    (RAW + "        with:\n          repository: someone/else\n", "writes a key of the step twice: with"),
    (RAW.replace("name: CI\n", "name: !unknown CI\n"), "is not valid YAML this can rewrite (ConstructorError)"),
    (RAW + "---\nname: second document\n", "is not valid YAML this can rewrite (ComposerError)"),
])
def test_what_the_write_cannot_handle_is_refused_at_read_time(text, said):
    both_refuse(text, said)


def test_an_unknown_tag_is_one_error_line_and_exit_2_not_a_traceback(tmp_path, capsys):
    f = tmp_path / "ci.yml"
    f.write_text(RAW.replace("name: CI\n", "name: !unknown CI\n"), encoding="utf-8")
    for cmd in (["gate-read", str(f), "owner/repo ci.yml", OWNER], ["gate-set", str(f), "owner/repo ci.yml", OWNER, B]):
        assert pins.main(cmd) == 2
        err = capsys.readouterr().err
        assert err.count("\n") == 1 and err.startswith("ERROR: owner/repo ci.yml: is not valid YAML this can rewrite")


SETUP_TEXT = f"# pin\nfleet_pin_commit={A}\nfleet_pin_sha256={'c' * 64}\nrest=1\n"
CODEX_TEXT = f"readonly fleet_pin_commit='{A}'\nreadonly fleet_pin_sha256='{'c' * 64}'\nrest=1\n"


def test_the_setup_rewrite_changes_the_commit_and_never_the_digest():
    after = pins.setup_set(SETUP_TEXT, B)
    assert after == SETUP_TEXT.replace(A, B)
    assert pins.setup_read(after) == (B, "c" * 64)


def test_the_codex_rewrite_changes_both_lines_and_nothing_else():
    after = pins.codex_set(CODEX_TEXT, B, "d" * 64)
    assert after == f"readonly fleet_pin_commit='{B}'\nreadonly fleet_pin_sha256='{'d' * 64}'\nrest=1\n"


@pytest.mark.parametrize("text", [
    SETUP_TEXT.replace(f"fleet_pin_commit={A}\n", ""),
    SETUP_TEXT + f"fleet_pin_commit={B}\n",
    SETUP_TEXT.replace("c" * 64, "c" * 63),
    SETUP_TEXT + f"fleet_pin_sha256={'d' * 64}\n",
    SETUP_TEXT.replace(f"fleet_pin_commit={A}", f"  fleet_pin_commit={A}"),
])
def test_a_setup_script_without_exactly_one_of_each_line_is_an_error(text):
    for call in (pins.setup_read, lambda t: pins.setup_set(t, B)):
        with pytest.raises(pins.ShapeError):
            call(text)


@pytest.mark.parametrize("text", [
    CODEX_TEXT.replace(f"readonly fleet_pin_commit='{A}'\n", ""),
    CODEX_TEXT + f"readonly fleet_pin_commit='{B}'\n",
    CODEX_TEXT.replace(f"'{'c' * 64}'", f"'{'c' * 60}'"),
    CODEX_TEXT.replace("readonly fleet_pin_sha256", "fleet_pin_sha256"),
])
def test_a_codex_script_without_exactly_one_of_each_line_is_an_error(text):
    for call in (pins.codex_read, lambda t: pins.codex_set(t, B, "d" * 64)):
        with pytest.raises(pins.ShapeError):
            call(text)


def test_the_command_names_the_label_not_the_path(tmp_path, capsys):
    f = tmp_path / "ci.yml"
    f.write_text(workflow(), encoding="utf-8")
    assert pins.main(["gate-read", str(f), "owner/repo ci.yml", OWNER]) == 2
    err = capsys.readouterr().err
    assert err.startswith("ERROR: owner/repo ci.yml: has 0 step(s)") and str(tmp_path) not in err


def test_a_refused_write_leaves_the_file_as_it_was(tmp_path):
    f = tmp_path / "ci.yml"
    text = workflow(gate(), gate())
    f.write_text(text, encoding="utf-8")
    assert pins.main(["gate-set", str(f), "label", OWNER, B]) == 2
    assert f.read_text(encoding="utf-8") == text
    assert pins.main(["gate-set", str(f), "label", OWNER, "not-a-sha"]) == 2
