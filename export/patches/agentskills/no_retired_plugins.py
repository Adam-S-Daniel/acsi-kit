"""setup.sh writes none of the source owner's retired plugin names.

The source's `setup.sh --owner-machine` writes `false` for every plugin of the
registry it retired (`RETIRED_PLUGINS`, ADR 0013), so a machine converged
under the old names never loads each skill twice. An adopter never had that
registry, so on the real walk on GitHub Free (acsi-kit PR #139) their
`~/.claude/settings.json` got five entries for plugins that never existed for
them. The list is the source's own data: this patch reads it from the
convergence block's AST, ships the tuple empty with a comment saying why,
and replaces the two tests that asserted its names with two that assert none
is written and that an entry a machine already has is left alone. Nothing is
hard-coded here: a re-pin that adds a name to the source's list empties it
too, and a source that drops the list stops the export. The test file's own
`RETIRED` list stays as the source has it: the new tests use it as the names
that must not appear, so a name the source adds to setup.sh but not there is
not checked by them (the kit test of the committed setup.sh still is).

Runs on the substituted tree.
"""

from __future__ import annotations

import ast
from pathlib import Path

SETUP = "setup.sh"
OPEN, CLOSE = "<<'PYEOF'\n", "\nPYEOF\n"
TESTS = "scripts/test_setup_settings_convergence.py"
OLD_TESTS = ("test_the_retired_registrys_plugins_end_disabled",
             "test_a_fresh_machine_gets_the_retired_names_as_inert_falses")

KIT_NOTE = (
    "# The adoption kit ships this list EMPTY: an adopter never had the source\n"
    "# owner's retired registry, so its plugin names are not written to an\n"
    "# adopter's settings at all. A registry you retire yourself goes here.\n"
)

NEW_TESTS = '''def test_the_kit_writes_no_retired_registry_names(tmp_path):
    """The adoption kit ships RETIRED_PLUGINS empty: an adopter never had the
    source owner's retired registry, so no entry for its plugins is written."""
    settings = converge(tmp_path)
    marketplaces = {name.split("@", 1)[1] for name in RETIRED}
    assert not [k for k in settings["enabledPlugins"] if k.split("@", 1)[-1] in marketplaces]
    assert not marketplaces & set(settings["extraKnownMarketplaces"])


def test_retired_entries_a_machine_already_has_are_left_alone(tmp_path):
    """Nothing here deletes or flips a key it does not write."""
    settings = converge(tmp_path, {"enabledPlugins": {name: True for name in RETIRED}})
    for name in RETIRED:
        assert settings["enabledPlugins"][name] is True, name
'''


def _line_offsets(text: str) -> list:
    out, pos = [], 0
    for line in text.splitlines(keepends=True):
        out.append(pos)
        pos += len(line)
    out.append(pos)
    return out


def _empty_list(setup: str) -> str:
    start = setup.index(OPEN) + len(OPEN)
    end = setup.index(CLOSE, start) + 1
    block = setup[start:end]
    nodes = [n for n in ast.parse(block).body
             if isinstance(n, ast.Assign) and [getattr(t, "id", None) for t in n.targets] == ["RETIRED_PLUGINS"]]
    if len(nodes) != 1 or not isinstance(nodes[0].value, ast.Tuple):
        raise SystemExit(f"no_retired_plugins: expected one RETIRED_PLUGINS = (...) tuple in {SETUP}'s convergence block")
    node = nodes[0]
    offs = _line_offsets(block)
    a = offs[node.lineno - 1] + node.col_offset
    b = offs[node.end_lineno - 1] + node.end_col_offset
    block = block[:a] + KIT_NOTE + "RETIRED_PLUGINS = ()" + block[b:]
    return setup[:start] + block + setup[end:]


def _replace_tests(text: str) -> str:
    tree = ast.parse(text)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    missing = [n for n in OLD_TESTS if n not in funcs]
    if missing or "RETIRED" not in {getattr(t, "id", None) for n in tree.body if isinstance(n, ast.Assign) for t in n.targets}:
        raise SystemExit(f"no_retired_plugins: {TESTS} lacks {missing or 'RETIRED'}")
    lines = text.splitlines(keepends=True)
    spans = sorted((funcs[n].lineno - 1, funcs[n].end_lineno) for n in OLD_TESTS)
    (s1, e1), (s2, e2) = spans
    if "".join(lines[e1:s2]).strip():
        raise SystemExit(f"no_retired_plugins: the two retired-name tests in {TESTS} are no longer adjacent")
    return "".join(lines[:s1]) + NEW_TESTS + "".join(lines[e2:])


def apply(root: Path, ctx) -> None:
    setup = root / SETUP
    setup.write_text(_empty_list(setup.read_text(encoding="utf-8")), encoding="utf-8")
    tests = root / TESTS
    tests.write_text(_replace_tests(tests.read_text(encoding="utf-8")), encoding="utf-8")
