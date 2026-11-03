"""DECISIONS C11: the skill freshness lint names only the kit's registries and repos.

scripts/skills_freshness.yml (new in the source, re-pin round 2 of
2026-11-03) says which repo each registry's skills describe. The source also
declares its platform repo and one consumer site as registries, with the
waivers for their skills, and names a personal tool repo of the source
owner's. The kit's scripts/skills_registries.yml no longer declares the two
sites (its own C11 edit), and the lint's shipped test requires every waiver
to name a declared registry, so:

- the two site registries are cut, with their comments;
- the `repos:` entry for the repo outside `kit_repos` is cut (C3's invented
  example sites stay: a sentence may still name them);
- every waiver is cut (each one is for a skill of a cut registry), leaving
  `waivers: []` under the comment that explains the format.

Runs on the substituted tree. After the cuts it checks that every registry
left is one skills_registries.yml declares and that every repo the file
names is in `kit_repos` (manifests/_common.yml).
"""

from __future__ import annotations

from pathlib import Path

import yaml

CONFIG = "scripts/skills_freshness.yml"
REGISTRIES = "scripts/skills_registries.yml"

# (start, end): remove from start (inclusive) to end (exclusive).
CUTS = [
    ("  example-site-platform:\n    repo: example-adopter/example-site-platform\n",
     "\n# Names a sentence may use for a repo"),
    ("waivers:\n  - skill: ", None),
]
LINES = [
    ("  claude-memory-map: example-adopter/claude-memory-map\n", ""),
]


def _cut(text: str, start: str, end: str | None) -> str:
    if text.count(start) != 1:
        raise SystemExit(f"kit_freshness: expected 1 of {start[:60]!r}, found {text.count(start)}")
    i = text.index(start)
    if end is None:
        return text[:i]
    j = text.find(end, i + len(start))
    if j < 0 or text.count(end) != 1:
        raise SystemExit(f"kit_freshness: expected 1 of {end[:60]!r} after the start")
    return text[:i] + text[j:]


def apply(root: Path, ctx) -> None:
    path = root / CONFIG
    text = path.read_text(encoding="utf-8")
    for start, end in CUTS:
        text = _cut(text, start, end)
    text += "waivers: []\n"
    for old, new in LINES:
        if text.count(old) != 1:
            raise SystemExit(f"kit_freshness: expected 1 of {old[:60]!r}, found {text.count(old)}")
        text = text.replace(old, new)
    doc = yaml.safe_load(text)
    declared = {r["name"] for r in yaml.safe_load((root / REGISTRIES).read_text(encoding="utf-8"))["registries"]}
    if set(doc["registries"]) != declared:
        raise SystemExit(f"kit_freshness: registries {sorted(doc['registries'])} != declared {sorted(declared)}")
    kit = set(ctx["common"]["kit_repos"])
    owners = set(ctx["common"]["kit_owners"])
    named = [r["repo"] for r in doc["registries"].values()] + list(doc["repos"].values())
    for slug in named:
        owner, _, repo = slug.partition("/")
        if owner not in owners or repo not in kit:
            raise SystemExit(f"kit_freshness: {CONFIG} still names {slug}, outside kit_repos")
    path.write_text(text, encoding="utf-8")
