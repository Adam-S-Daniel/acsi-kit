"""DECISIONS "Re-pin of the private registry (2026-11-26)": the source owner's own machinery stays out.

The private registry's source carries workflows, hooks and infrastructure
that serve only its owner, outside the include list, and an eval-protection
gate in agent-checks.yml that checks out the owner's repos at the owner's
commits. The include list keeps those files out; this cuts what the shipped
files say about them, so nothing names or runs a part the adopter does not
have:

- agent-checks.yml: the eval-protection steps (the kit's private registry
  ships no skills, so the gate has nothing to protect, and on the base track
  there is no skills-evals to check out) and the job permissions they needed.
  Only those steps go: the cut fails if the tail it removes holds any other.
- actions.lock: the entries of workflows that are not in the tree, and the
  tags only those used.
- AGENTS.md: the repo-specific sections after the starter's marker comment.
- README.md: the paragraphs about the bundle's hooks.

Runs on the substituted tree, before the regenerate steps (which rebuild
AGENTS.md's managed half from what is left). Every cut checks its shape and
fails loudly, so a source change that moves a block stops the export.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

AGENT_CHECKS = ".github/workflows/agent-checks.yml"
LOCK = ".github/workflows/actions.lock"
MARKER = "<!-- Add your repo-specific agent guidance below this line -->"
GATE_COMMENT = "      # _agent-guidance ADR 0034:"
PERMS = (
    "    # pull-requests: read for the eval-protection step, which reads the PR's\n"
    "    # body and file list fresh from the API.\n"
    "    permissions:\n"
    "      contents: read\n"
    "      pull-requests: read\n"
)
# The gate's steps, by name, in the source's order: only these may go.
GATE_STEPS = ("Check out the eval-protection gate", "Check out the skills-evals gate input builder",
              "Eval-protected skills take correctness fixes only")
# The job permissions the gate needed, which go with it.
GATE_PERMISSIONS = {"contents": "read", "pull-requests": "read"}
HOOKS_START = "The bundle also carries one Claude Code Stop hook,"
HOOKS_END = "cannot send it itself.\n\n"


class PatchError(SystemExit):
    pass


def _once(text: str, needle: str, where: str) -> int:
    n = text.count(needle)
    if n != 1:
        raise PatchError(f"owner_only: {where}: expected 1 of {needle[:60]!r}, found {n}")
    return text.index(needle)


def _doc(text: str) -> dict:
    try:
        doc = yaml.safe_load(text)
        doc["jobs"]["agent-checks"]["steps"]
        return doc
    except (yaml.YAMLError, KeyError, TypeError):
        raise PatchError(f"owner_only: {AGENT_CHECKS}: no agent-checks job with steps") from None


def cut_gate(text: str) -> str:
    """agent-checks.yml without the eval-protection steps and their permissions.

    The gate is the job's last steps, from its comment to the end of the file.
    The cut parses the whole document before and after, and refuses unless
    the only difference is the gate's own steps (GATE_STEPS, by name, all of
    them) and the permissions they needed. So a step or a job the source adds
    after the gate, or a new step that checks out another repo, stops the
    export instead of vanishing."""
    before = _doc(text)
    i = _once(text, "\n" + GATE_COMMENT, AGENT_CHECKS)
    text = text[:i + 1].rstrip("\n") + "\n"
    _once(text, PERMS, AGENT_CHECKS)
    text = text.replace(PERMS, "")
    after = _doc(text)
    job = before["jobs"]["agent-checks"]
    if [s.get("name") for s in job["steps"] if s.get("name") in GATE_STEPS] != list(GATE_STEPS):
        raise PatchError(f"owner_only: {AGENT_CHECKS}: the gate's steps are not the ones this cut knows: {GATE_STEPS}")
    if job.get("permissions") != GATE_PERMISSIONS:
        raise PatchError(f"owner_only: {AGENT_CHECKS}: the job's permissions are not the gate's")
    want = copy.deepcopy(before)
    want["jobs"]["agent-checks"]["steps"] = [s for s in job["steps"] if s.get("name") not in GATE_STEPS]
    del want["jobs"]["agent-checks"]["permissions"]
    if after != want:
        raise PatchError(f"owner_only: {AGENT_CHECKS}: the cut would remove more than the gate's steps and permissions")
    return text


def cut_lock(text: str, present: set) -> str:
    """actions.lock with only the workflows in the tree, and the tags they use.
    Cuts whole entries at the lines the parse gives, so the rest keeps its form."""
    doc = yaml.safe_load(text)
    keep_wf = {w: uses for w, uses in doc["workflows"].items() if w in present}
    used = {u for uses in keep_wf.values() for u in (uses or [])}
    lines = text.splitlines(True)
    out, skip, section = [], False, None
    for line in lines:
        stripped = line.rstrip("\n")
        if not line.startswith(" "):
            section, skip = stripped.rstrip(":"), False
            out.append(line)
            continue
        if line.startswith("    '") and not line.startswith("     "):
            key = stripped.strip().rstrip(":").rstrip(" []").rstrip(":").strip("'")
            if section == "workflows":
                skip = key not in keep_wf
            elif section == "dependencies":
                skip = key not in used
        if not skip:
            out.append(line)
    new = "".join(out)
    got = yaml.safe_load(new)
    want = dict(doc, workflows=keep_wf, dependencies={k: v for k, v in doc["dependencies"].items() if k in used})
    if got != want:
        raise PatchError(f"owner_only: {LOCK}: the cut would change more than the left-out entries")
    return new


def cut_agents(text: str) -> str:
    i = _once(text, MARKER, "AGENTS.md")
    return text[:i + len(MARKER)] + "\n"


def cut_readme(text: str) -> str:
    i = _once(text, HOOKS_START, "README.md")
    j = _once(text, HOOKS_END, "README.md")
    if j < i:
        raise PatchError("owner_only: README.md: the hooks paragraphs are out of order")
    return text[:i] + text[j + len(HOOKS_END):]


def apply(root: Path, ctx) -> None:
    p = root / AGENT_CHECKS
    p.write_text(cut_gate(p.read_text(encoding="utf-8")), encoding="utf-8")
    present = {f".github/workflows/{q.name}" for q in (root / ".github/workflows").glob("*.yml")}
    p = root / LOCK
    p.write_text(cut_lock(p.read_text(encoding="utf-8"), present), encoding="utf-8")
    p = root / "AGENTS.md"
    p.write_text(cut_agents(p.read_text(encoding="utf-8")), encoding="utf-8")
    p = root / "README.md"
    p.write_text(cut_readme(p.read_text(encoding="utf-8")), encoding="utf-8")
