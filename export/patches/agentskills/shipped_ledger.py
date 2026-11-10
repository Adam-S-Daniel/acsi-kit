"""The shipped-names ledger lists only names the adopter's registry has.

`scripts/shipped_names.json` (adam-agentskills#133) is the append-only record
of every marketplace, plugin and `<plugin>/<skill>` name that has shipped,
and two checks read it as "retired":

- `scripts/check_one_way_doors.py` fails a pull request that adds a skill
  whose basename the base's ledger lists, unless the body carries an
  `Adversarial-review: pass` line;
- skills-evals' `draft_new_skill.py` name-check refuses a drafted skill
  whose name the ledger lists.

Exported as the source has it, the ledger named every skill the source owner
ever shipped, about twenty more than the kit's registry ships, including
the five library skills. An adopter who added `writing-adrs` with
add-content.sh after their repos existed got a red required check on that
pull request, and the draft lane could never propose a skill under any of
those names.

So, on the substituted tree, after library_skills.py and blank_registry.py:

- `skills` keeps the skills this registry ships (a SKILL.md on disk) and
  the whole-skill removals the exported docs/skill-impact.md records for a
  plugin of this marketplace, which the starter's own test requires;
- `plugins` keeps the plugins the marketplace lists;
- `marketplace` keeps the marketplace's name.

Canonical form (json.dumps(indent=2) plus newline, sorted and unique), as the
starter's ledger test requires. Library skills a later install adds are not
appended: names present at a pull request's base count as shipped whether or
not the ledger lists them (check_one_way_doors.py's docstring).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# A skill-impact heading: `## <date> — <plugin>/<skill> — <kind>`.
HEADING = re.compile(r"^## \d{4}-\d{2}-\d{2} — ([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+) — (\w+)\s*$")


def apply(root: Path, ctx) -> None:
    path = root / "scripts" / "shipped_names.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    market = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    plugins = {entry["name"] for entry in market["plugins"]}

    on_disk = {f"{p.parent.parent.parent.name}/{p.parent.name}"
               for p in (root / "plugins").glob("*/skills/*/SKILL.md")}
    impact = (root / "docs" / "skill-impact.md").read_text(encoding="utf-8")
    removed = {f"{m.group(1)}/{m.group(2)}" for m in map(HEADING.match, impact.splitlines())
               if m and m.group(3) == "remove" and m.group(1) in plugins}

    missing = sorted((on_disk | removed) - set(ledger["skills"]))
    if missing:
        raise RuntimeError(f"shipped_names.json: the source ledger lacks {missing}; read the source before trimming")
    ledger["marketplace"] = [market["name"]]
    ledger["plugins"] = sorted(n for n in ledger["plugins"] if n in plugins)
    ledger["skills"] = sorted(on_disk | removed)
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
