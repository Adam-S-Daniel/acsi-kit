#!/usr/bin/env python3
"""guidance_pins.py <command> <file> <label> [args]

Finds and rewrites the places in an adopter's repos that name a commit of
their _agent-guidance (regenerate.sh's run-health-sha and codex-pin tasks;
export/tests/test_guidance_pins.py runs the same locators over the kit's own
starter trees, so a source change that moves one fails there first).

  setup-read <cloud-env-setup.sh> <label>
      prints "<fleet_pin_commit> <fleet_pin_sha256>": acsi-agentskills'
      scripts/cloud-env-setup.sh, the one `fleet_pin_commit=<40 hex>` line and
      the one `fleet_pin_sha256=<64 hex>` line.
  setup-set <cloud-env-setup.sh> <label> <commit>
      rewrites the commit line. The digest line is never written.
  gate-read <ci.yml> <label> <owner>
      prints the `with.ref` of the one step named GATE_STEP, whose
      `with.repository` must be <owner>/_agent-guidance: acsi-agentskills'
      .github/workflows/ci.yml, parsed with PyYAML.
  gate-set <ci.yml> <label> <owner> <commit>
      rewrites that step's ref, at the position the parser gives for it, so
      the same commit in another step stays as it is; then parses the result
      and checks that nothing else in the document changed.
  codex-read <sync-codex-cloud-environments.sh> <label>
      prints "<fleet_pin_commit> <fleet_pin_sha256>": wsl-automation's
      `readonly fleet_pin_commit='<40 hex>'` and
      `readonly fleet_pin_sha256='<64 hex>'` lines, one of each.
  codex-set <sync-codex-cloud-environments.sh> <label> <commit> <sha256>
      rewrites both.

<label> is how messages name the file (owner/repo and path): the path given
is a temporary clone's. A file that does not have exactly the shape above is
an error (exit 2, one "ERROR: <label>: ..." line), never a skip. A write
that would change nothing writes nothing. Needs PyYAML for the gate commands.
"""
import copy
import re
import sys

GATE_STEP = "Check out the eval-protection gate"
GUIDANCE_REPO = "_agent-guidance"
SHA40 = re.compile(r"[0-9a-f]{40}")
SHA64 = re.compile(r"[0-9a-f]{64}")

SETUP_COMMIT = re.compile(r"(?m)^fleet_pin_commit=([0-9a-f]{40})$")
SETUP_DIGEST = re.compile(r"(?m)^fleet_pin_sha256=([0-9a-f]{64})$")
CODEX_COMMIT = re.compile(r"(?m)^readonly fleet_pin_commit='([0-9a-f]{40})'$")
CODEX_DIGEST = re.compile(r"(?m)^readonly fleet_pin_sha256='([0-9a-f]{64})'$")


class ShapeError(Exception):
    """The file does not have the one pin this looks for."""


def _one(pattern, text, what):
    found = list(pattern.finditer(text))
    if len(found) != 1:
        raise ShapeError(f"has {len(found)} `{what}` line(s), want exactly 1")
    return found[0]


def _replace(text, match, value):
    start, end = match.span(1)
    return text[:start] + value + text[end:]


def setup_read(text):
    """(commit, digest) of the fleet-guidance pin in cloud-env-setup.sh."""
    commit = _one(SETUP_COMMIT, text, "fleet_pin_commit=<40 hex>")
    digest = _one(SETUP_DIGEST, text, "fleet_pin_sha256=<64 hex>")
    return commit.group(1), digest.group(1)


def setup_set(text, commit):
    setup_read(text)   # both lines, or an error: never half a pin
    return _replace(text, _one(SETUP_COMMIT, text, "fleet_pin_commit=<40 hex>"), commit)


def codex_read(text):
    """(commit, digest) of the fleet-guidance pin in sync-codex-cloud-environments.sh."""
    commit = _one(CODEX_COMMIT, text, "readonly fleet_pin_commit='<40 hex>'")
    digest = _one(CODEX_DIGEST, text, "readonly fleet_pin_sha256='<64 hex>'")
    return commit.group(1), digest.group(1)


def codex_set(text, commit, digest):
    codex_read(text)
    text = _replace(text, _one(CODEX_COMMIT, text, "readonly fleet_pin_commit='<40 hex>'"), commit)
    return _replace(text, _one(CODEX_DIGEST, text, "readonly fleet_pin_sha256='<64 hex>'"), digest)


def _child(node, key):
    """The value node under `key` of a YAML mapping node, or None."""
    import yaml
    if not isinstance(node, yaml.MappingNode):
        return None
    for k, v in node.value:
        if isinstance(k, yaml.ScalarNode) and k.value == key:
            return v
    return None


def _gate_ref_node(text, owner):
    """The scalar node holding the gate step's with.ref, after every check."""
    import yaml
    try:
        root = yaml.compose(text)
    except yaml.YAMLError as e:
        raise ShapeError(f"is not valid YAML ({type(e).__name__})") from None
    jobs = _child(root, "jobs")
    steps = []
    for _, job in (jobs.value if isinstance(jobs, yaml.MappingNode) else []):
        seq = _child(job, "steps")
        for step in (seq.value if isinstance(seq, yaml.SequenceNode) else []):
            name = _child(step, "name")
            if isinstance(name, yaml.ScalarNode) and name.value == GATE_STEP:
                steps.append(step)
    if len(steps) != 1:
        raise ShapeError(f'has {len(steps)} step(s) named "{GATE_STEP}", want exactly 1')
    with_ = _child(steps[0], "with")
    repo, ref = _child(with_, "repository"), _child(with_, "ref")
    want = f"{owner}/{GUIDANCE_REPO}"
    if not isinstance(repo, yaml.ScalarNode) or repo.value.lower() != want.lower():
        got = repo.value if isinstance(repo, yaml.ScalarNode) else "nothing"
        raise ShapeError(f'the step "{GATE_STEP}" checks out {got}, want {want}')
    if not isinstance(ref, yaml.ScalarNode) or not SHA40.fullmatch(ref.value):
        raise ShapeError(f'the step "{GATE_STEP}" has no with.ref of 40 hex characters')
    if text[ref.start_mark.index:ref.end_mark.index] != ref.value:
        raise ShapeError(f'the step "{GATE_STEP}" writes its with.ref quoted or folded; write it as a plain 40 hex value')
    return ref


def gate_read(text, owner):
    """The commit the eval-protection gate's checkout step names."""
    return _gate_ref_node(text, owner).value


def gate_set(text, owner, commit):
    import yaml
    ref = _gate_ref_node(text, owner)
    new = text[:ref.start_mark.index] + commit + text[ref.end_mark.index:]
    # The proof: the step's ref is the new commit, and the parsed document is
    # otherwise the one it was.
    want = copy.deepcopy(yaml.safe_load(text))
    hits = 0
    for job in want["jobs"].values():
        for step in (job.get("steps") or []) if isinstance(job, dict) else []:
            if isinstance(step, dict) and step.get("name") == GATE_STEP:
                step["with"]["ref"] = commit
                hits += 1
    if hits != 1 or gate_read(new, owner) != commit or yaml.safe_load(new) != want:
        raise ShapeError("the rewrite of the gate step's ref changed something else, so nothing was written")
    return new


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    arity = {"setup-read": 0, "setup-set": 1, "gate-read": 1, "gate-set": 2, "codex-read": 0, "codex-set": 2}
    if len(argv) < 3 or argv[0] not in arity or len(argv) != 3 + arity[argv[0]]:
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        return 2
    cmd, path, label, rest = argv[0], argv[1], argv[2], argv[3:]
    commit = {"setup-set": 0, "gate-set": 1, "codex-set": 0}.get(cmd)
    if commit is not None and not SHA40.fullmatch(rest[commit]):
        print(f"ERROR: {cmd}: the commit must be 40 hex characters", file=sys.stderr)
        return 2
    if cmd == "codex-set" and not SHA64.fullmatch(rest[1]):
        print("ERROR: codex-set: the sha256 must be 64 hex characters", file=sys.stderr)
        return 2
    try:
        with open(path, "rb") as f:
            text = f.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"ERROR: {label}: cannot be read ({type(e).__name__})", file=sys.stderr)
        return 2
    try:
        if cmd == "setup-read":
            print(*setup_read(text))
        elif cmd == "codex-read":
            print(*codex_read(text))
        elif cmd == "gate-read":
            print(gate_read(text, rest[0]))
        else:
            new = {"setup-set": setup_set, "gate-set": gate_set, "codex-set": codex_set}[cmd](text, *rest)
            if new != text:
                with open(path, "wb") as f:   # in place: the file keeps its mode
                    f.write(new.encode("utf-8"))
    except ShapeError as e:
        print(f"ERROR: {label}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
