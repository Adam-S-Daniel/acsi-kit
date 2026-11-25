"""A machine name is replaced in every letter case and inside identifiers.

The workstation-name rule in manifests/_common.yml is a `regex` + `forms`
rule that spells the name one letter class at a time (`[Xx][Yy]...`), so the
kit's own text never holds it. A word-bounded, case-sensitive rule once let
nine lowercase identifiers built on the name through (a function, its
parameters and a test class). These tests use an invented stand-in name
through a test-only rule set, never the real one.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

EXPORT_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("kit_export", EXPORT_DIR / "export.py")
export = sys.modules.get("kit_export") or importlib.util.module_from_spec(_spec)
if "kit_export" not in sys.modules:
    sys.modules["kit_export"] = export
    _spec.loader.exec_module(export)

STAND_IN = "zephyrbox"  # invented
CLASSES = "".join(f"[{c.upper()}{c.lower()}]" for c in STAND_IN)
RULES = [{"name": "stand-in machine", "regex": CLASSES, "to": "WORKSTATION", "forms": True}]


def _sub(text: str, path: str = "x.py") -> str:
    return export.Substituter(export.compile_rules(RULES)).sub(text, path)


@pytest.mark.parametrize("before, after", [
    ("on ZEPHYRBOX today", "on WORKSTATION today"),                  # all upper
    ("ssh zephyrbox", "ssh workstation"),                            # lowercase word
    ("Zephyrbox is up", "Workstation is up"),                        # capitalized word
    ("def scan_zephyrbox_tasks(x):", "def scan_workstation_tasks(x):"),  # snake_case
    ("zephyrbox_tasks = []", "workstation_tasks = []"),
    ("ZEPHYRBOX_TASKS = 1", "WORKSTATION_TASKS = 1"),                # SCREAMING_CASE
    ("const zephyrboxTasks = []", "const workstationTasks = []"),    # camelCase, leading
    ("scanZephyrboxTasks()", "scanWorkstationTasks()"),              # camelCase, inner
    ("class ZephyrboxTasks:", "class WorkstationTasks:"),            # PascalCase
    ("--zephyrbox-tasks", "--workstation-tasks"),                    # kebab-case
    ("SCAN-ZEPHYRBOX-1", "SCAN-WORKSTATION-1"),                      # upper kebab
    ("zEpHyRbOx", "Workstation"),                                    # odd mixed case
])
def test_every_case_style_is_replaced_in_its_style(before, after):
    assert _sub(before) == after


def test_a_path_takes_the_same_replacement():
    # export_repo substitutes each path with the same Substituter as the text.
    assert _sub("scripts/zephyrbox_tasks.py", "scripts/zephyrbox_tasks.py") == "scripts/workstation_tasks.py"
    assert _sub("docs/Zephyrbox-setup.md", "docs/Zephyrbox-setup.md") == "docs/Workstation-setup.md"


def test_a_definition_and_its_callers_get_one_name():
    source = (
        "def scan_zephyrbox_tasks(checkout):\n"
        "    return [checkout]\n\n"
        "def breakdown(zephyrbox):\n"
        "    return [b for b in zephyrbox]\n\n"
        "class ZephyrboxTasks:\n"
        "    def test_zephyrbox_task(self):\n"
        "        return breakdown(zephyrbox=scan_zephyrbox_tasks('.'))\n"
    )
    out = _sub(source)
    assert STAND_IN not in out.lower()
    tree = ast.parse(out)  # still valid Python
    defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    params = {a.arg for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) for a in n.args.args}
    keywords = {k.arg for n in ast.walk(tree) if isinstance(n, ast.Call) for k in n.keywords}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert {"scan_workstation_tasks", "breakdown", "WorkstationTasks", "test_workstation_task"} <= defs
    assert calls <= defs
    assert "workstation" in params and keywords == {"workstation"} and "workstation" in names


def test_a_longer_word_holding_the_name_is_replaced_too():
    # Decision: no word boundary. A machine name inside any identifier or word
    # is replaced, because the owner's private scan matches it in any case and
    # anywhere. A longer unrelated word reads oddly afterwards, which the
    # `--check` diff of a re-pin shows a maintainer; leaving it would publish
    # the name.
    assert _sub("unzephyrboxed") == "unworkstationed"
    assert _sub("ZEPHYRBOXES") == "WORKSTATIONES"


def test_a_regex_with_forms_needs_a_one_word_replacement():
    with pytest.raises(export.ExportError, match="one-word"):
        export.compile_rules([{"name": "x", "regex": CLASSES, "to": "two-words", "forms": True}])
