"""DECISIONS "Re-pin of the private registry (2026-11-26)": the source owner's own machinery stays out.

The private registry's source now carries what serves only its owner: the
eval-results lane and private explorer (eval-results-*.yml,
explorer-private.yml), the usage sink (infrastructure/usage-sink/,
usage-sink-ingest.yml, and the bundle's two Stop hooks that send records to
it), and an eval-protection gate in agent-checks.yml that checks out the
owner's _agent-guidance and skills-evals at the owner's commits. The include
list already keeps those files out; this cuts what the shipped files say
about them, so nothing names or runs a part the adopter does not have:

- agent-checks.yml: the eval-protection steps (the kit's private registry
  ships no skills, so the gate has nothing to protect, and on the base track
  there is no skills-evals to check out) and the job permissions they needed.
- actions.lock: the entries of workflows that are not in the tree, and the
  tags only those used.
- AGENTS.md: the repo-specific sections after the starter's marker comment
  (they describe the left-out workflows and the usage-sink stack).
- README.md: the paragraphs about the bundle's Stop hooks.

Runs on the substituted tree, before the regenerate steps (which rebuild
AGENTS.md's managed half from what is left). Every cut checks its shape and
fails loudly, so a source change that moves a block stops the export.
"""

from __future__ import annotations

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
HOOKS_START = "The bundle also carries one Claude Code Stop hook,"
HOOKS_END = "cannot send it itself.\n\n"


class PatchError(SystemExit):
    pass


def _once(text: str, needle: str, where: str) -> int:
    n = text.count(needle)
    if n != 1:
        raise PatchError(f"owner_only: {where}: expected 1 of {needle[:60]!r}, found {n}")
    return text.index(needle)


def cut_gate(text: str) -> str:
    """agent-checks.yml without the eval-protection steps and their permissions."""
    i = _once(text, "\n" + GATE_COMMENT, AGENT_CHECKS)
    text = text[:i + 1].rstrip("\n") + "\n"
    _once(text, PERMS, AGENT_CHECKS)
    text = text.replace(PERMS, "")
    steps = yaml.safe_load(text)["jobs"]["agent-checks"]["steps"]
    if any("eval-protection" in yaml.safe_dump(s) or (s.get("with") or {}).get("repository") for s in steps):
        raise PatchError(f"owner_only: {AGENT_CHECKS}: a step still checks out another repo or names the gate")
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
