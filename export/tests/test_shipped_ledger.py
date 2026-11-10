"""The registry's shipped-names ledger never lists a skill the adopter can add.

The ledger (`starter/agent-skills/scripts/shipped_names.json`) is read as
"retired" by the one-way-door check and the draft lane's name-check. When it
was exported as the source had it, it listed the five library skills, so
adding one with add-content.sh after the repos existed failed a required
check (export/patches/agentskills/shipped_ledger.py has the story).

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import json
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
REG = KIT / "starter" / "agent-skills"


def test_no_library_skill_is_recorded_as_shipped():
    ledger = json.loads((REG / "scripts" / "shipped_names.json").read_text(encoding="utf-8"))
    shipped = {name.split("/", 1)[1] for name in ledger["skills"]}
    library = {p.name for p in (KIT / "library" / "skills").iterdir() if p.is_dir()}
    assert library, "library/skills is empty; the test lost its subject"
    assert sorted(shipped & library) == []


def test_every_skill_the_registry_ships_is_in_the_ledger():
    ledger = json.loads((REG / "scripts" / "shipped_names.json").read_text(encoding="utf-8"))
    on_disk = {f"{p.parent.parent.parent.name}/{p.parent.name}"
               for p in (REG / "plugins").glob("*/skills/*/SKILL.md")}
    assert on_disk and on_disk <= set(ledger["skills"])
