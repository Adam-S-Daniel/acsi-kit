"""Every routine's settings table in docs/routines.md names a model.

A routine saved with its model selector on Default runs the account's
default model, which is Opus on Pro and weighs more per token than Sonnet
(docs/before-you-start.md, "On Pro"). So each `Setting | Value` table on the
page has a `Model` row, and every routine a quick start step sends the
adopter to (the required steps of bootstrap/steps.json that link a section
of the page) has such a table. The page is parsed with markdown-it-py.

Run: python3 -m pytest export/tests/test_routine_tables.py -q
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from markdown_it import MarkdownIt

KIT = Path(__file__).resolve().parents[2]
PAGE = "docs/routines.md"


def settings_tables(text: str) -> dict[str, list[list[str]]]:
    """h2 heading -> one list of first-column cells per `Setting | Value` table under it."""
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    out: dict[str, list[list[str]]] = {}
    heading, rows, row, in_table = None, [], [], False
    for i, t in enumerate(tokens):
        if t.type == "heading_open" and t.tag == "h2":
            heading = tokens[i + 1].content
        elif t.type == "table_open":
            in_table, rows = True, []
        elif in_table and t.type in ("th_open", "td_open"):
            row.append(tokens[i + 1].content.strip())
        elif in_table and t.type == "tr_close":
            rows.append(row)
            row = []
        elif t.type == "table_close":
            in_table = False
            if rows and rows[0] == ["Setting", "Value"]:
                out.setdefault(heading, []).append([r[0] for r in rows[1:]])
    return out


def anchor(heading: str) -> str:
    """GitHub's anchor for a plain heading: lowercase, punctuation dropped, spaces to hyphens."""
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.lower()))


def missing_model(text: str) -> list[str]:
    return sorted(h for h, tables in settings_tables(text).items() for first in tables if "Model" not in first)


def test_every_settings_table_on_the_page_has_a_model_row():
    text = (KIT / PAGE).read_text(encoding="utf-8")
    assert len(settings_tables(text)) >= 6, "the scan found fewer routine tables than the page has"
    assert missing_model(text) == []


def test_every_routine_a_step_links_has_a_settings_table():
    text = (KIT / PAGE).read_text(encoding="utf-8")
    have = {anchor(h) for h in settings_tables(text)}
    steps = json.loads((KIT / "bootstrap/steps.json").read_text(encoding="utf-8"))["steps"]
    # A required step: the optional dashboard step links a section that describes pages, not one routine.
    linked = {s["link"].split("#", 1)[1]: s["id"] for s in steps
              if s.get("link", "").startswith(PAGE + "#") and not s.get("optional")}
    assert len(linked) >= 5, "the scan found fewer routine steps than steps.json has"
    assert {a: sid for a, sid in linked.items() if a not in have} == {}


def test_a_table_without_a_model_row_is_found():
    page = ("# Routines\n\n## One\n\n| Setting | Value |\n|---|---|\n| Trigger | API |\n| Model | Sonnet |\n\n"
            "## Two\n\n| Setting | Value |\n|---|---|\n| Trigger | API |\n| Spec | a file |\n\n"
            "## Not a routine\n\n| Name | Meaning |\n|---|---|\n| x | y |\n")
    assert sorted(settings_tables(page)) == ["One", "Two"]
    assert missing_model(page) == ["Two"]
