"""patches/agentskills/no_retired_plugins.py: no retired plugin names for an adopter.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

EXPORT_DIR = Path(__file__).resolve().parents[1]
KIT = EXPORT_DIR.parent
_spec = importlib.util.spec_from_file_location(
    "kit_patch_no_retired_plugins", EXPORT_DIR / "patches" / "agentskills" / "no_retired_plugins.py")
patch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(patch)

SETUP = """#!/usr/bin/env bash
echo before
"${PYTHON_CMD[@]}" - <<'PYEOF'
# comment — with an em dash
RETIRED_PLUGINS = (
    "a@old",
    "b@old-private",
)
TARGET = {"x": True}
TARGET.update({name: False for name in RETIRED_PLUGINS})
PYEOF
echo after
"""

TESTS = '''RETIRED = ["a@old", "b@old-private"]


def test_the_retired_registrys_plugins_end_disabled(tmp_path):
    assert old


def test_a_fresh_machine_gets_the_retired_names_as_inert_falses(tmp_path):
    assert old


def test_other():
    pass
'''


def tree(tmp_path: Path, setup: str = SETUP, tests: str = TESTS) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "setup.sh").write_text(setup, encoding="utf-8")
    (tmp_path / patch.TESTS).write_text(tests, encoding="utf-8")
    return tmp_path


def block(text: str) -> str:
    start = text.index(patch.OPEN) + len(patch.OPEN)
    return text[start:text.index(patch.CLOSE, start)]


def retired_value(text: str):
    for n in ast.parse(block(text)).body:
        if isinstance(n, ast.Assign) and [getattr(t, "id", None) for t in n.targets] == ["RETIRED_PLUGINS"]:
            return ast.literal_eval(n.value)
    raise AssertionError("no RETIRED_PLUGINS")


def test_the_list_ships_empty_and_the_rest_stays(tmp_path):
    root = tree(tmp_path)
    patch.apply(root, {})
    text = (root / "setup.sh").read_text()
    assert retired_value(text) == ()
    assert "@old" not in text
    assert text.startswith("#!/usr/bin/env bash\necho before\n")
    assert text.endswith('TARGET = {"x": True}\nTARGET.update({name: False for name in RETIRED_PLUGINS})\nPYEOF\necho after\n')
    assert patch.KIT_NOTE in text


def test_the_two_name_tests_are_replaced(tmp_path):
    root = tree(tmp_path)
    patch.apply(root, {})
    text = (root / patch.TESTS).read_text()
    assert "assert old" not in text
    assert text == 'RETIRED = ["a@old", "b@old-private"]\n\n\n' + patch.NEW_TESTS + "\n\ndef test_other():\n    pass\n"


def test_a_source_without_the_list_stops_the_export(tmp_path):
    root = tree(tmp_path, setup=SETUP.replace("RETIRED_PLUGINS = (", "OTHER = ("))
    with pytest.raises(SystemExit, match="expected one RETIRED_PLUGINS"):
        patch.apply(root, {})


def test_a_moved_test_stops_the_export(tmp_path):
    root = tree(tmp_path, tests=TESTS.replace("def test_a_fresh_machine_gets", "def test_x_gets"))
    with pytest.raises(SystemExit, match="lacks"):
        patch.apply(root, {})


def test_the_committed_starter_writes_no_retired_name():
    text = (KIT / "starter" / "agent-skills" / "setup.sh").read_text(encoding="utf-8")
    assert retired_value(text) == ()
    assert "@retired-agentskills" not in block(text)
