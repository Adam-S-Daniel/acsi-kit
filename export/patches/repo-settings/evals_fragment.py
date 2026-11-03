"""DECISIONS C13: fleet.yml declares the base repos only; skills-evals' element
moves to a fragment, repo-settings/fleet.evals.yml, that /adopt-evals merges.

The source's fleet.yml declares skills-evals with a ruleset bypass for the
roster App ("${ROSTER_WRITER_APP_ID}", C12). A base-only setup has neither
that repo nor that App, so with the element in fleet.yml the starter's own
repo-settings.yml `plan` job (which reads the committed fleet.yml) could not
plan. This patch moves the element out, structurally:

- fleet.yml is composed with PyYAML (a node tree with line marks, never a
  regex or an anchor text), the `repos:` element whose `name` is
  `<owner>/skills-evals` is found by its parsed name, and it must be found
  exactly once, or the export fails;
- its lines (from its `- name:` line to the end of its last value, with the
  comments inside it) are cut from fleet.yml and written, unchanged, under
  `repos:` in the fragment, after a header that says what the file is. The
  comment block above the element stays in fleet.yml: it describes the
  required checks of several repos, not this one;
- both files are parsed again: fleet.yml must hold what it held minus that
  element, and the fragment exactly that element.

Lines are moved byte for byte, so the comments and formatting stay as the
source has them, and a daily re-sync breaks only if the element itself
disappears or is duplicated.

The shipped tests read fleet.yml plus the fragment while the fragment exists
(TEST_LOADER below), so every assertion about skills-evals still holds; new
tests (FRAGMENT_TESTS) lock the split. One test that read fleet.yml's text
for the roster App's variable reads both files.

Runs after kit_config.py (which edits that element's comments and actor id).
"""

from __future__ import annotations

from pathlib import Path

import yaml

FLEET = "repo-settings/fleet.yml"
FRAGMENT = "repo-settings/fleet.evals.yml"
REPO = "skills-evals"

HEADER = """\
# fleet.evals.yml: the evals track's part of fleet.yml (the adoption kit's
# export/DECISIONS.md C13).
#
# fleet.yml declares the base repos only, so a setup without evals (no
# skills-evals repo, no roster App) plans and applies cleanly, and
# repo-settings.yml's plan job needs only the GUIDANCE_SYNC_APP_ID variable.
# This file holds skills-evals' element, exactly as it reads under
# fleet.yml's `repos:`. The engine and the workflows never read this file:
# until it is merged, nothing applies to skills-evals.
#
# Merging it: /adopt-evals runs the kit's `bootstrap/regenerate.sh
# evals-fleet`, once skills-evals exists and before the settings apply that
# protects it. That parses both files, appends each element below to
# fleet.yml's `repos:` list (an element fleet.yml already declares is left
# as it is), deletes this file, and proposes both changes in one pull
# request. By hand: move the element to the end of fleet.yml's `repos:`
# list and delete this file, in one pull request.
#
# tests/test_repo_settings.py reads fleet.yml plus this file while it exists,
# and refuses a repo declared in both.
"""


def _fail(msg: str):
    raise SystemExit(f"evals_fragment: {msg}")


def _is_repo(item: yaml.Node, repo: str) -> bool:
    if not isinstance(item, yaml.MappingNode):
        return False
    for k, v in item.value:
        if isinstance(k, yaml.ScalarNode) and k.value == "name" and isinstance(v, yaml.ScalarNode):
            return v.value.split("/", 1)[-1] == repo
    return False


def _last_line(node: yaml.Node) -> int:
    """The 0-based line of the node's last character: the deepest scalars'
    and flow collections' end marks (a block collection's own end mark is
    the start of whatever follows it, comments skipped, so it is not used)."""
    if isinstance(node, yaml.ScalarNode) or getattr(node, "flow_style", False):
        m = node.end_mark
        return m.line if m.column > 0 else m.line - 1
    children = node.value if isinstance(node, yaml.SequenceNode) else [n for kv in node.value for n in kv]
    return max(_last_line(c) for c in children)


def element_span(text: str, repo: str) -> tuple[int, int]:
    """[first, last] 0-based lines of the one `repos:` element naming `repo`."""
    root = yaml.compose(text)
    if not isinstance(root, yaml.MappingNode):
        _fail("fleet.yml's top level is not a map")
    seqs = [v for k, v in root.value if isinstance(k, yaml.ScalarNode) and k.value == "repos"]
    if len(seqs) != 1 or not isinstance(seqs[0], yaml.SequenceNode) or seqs[0].flow_style:
        _fail("fleet.yml has no single block `repos:` list")
    found = [item for item in seqs[0].value if _is_repo(item, repo)]
    if len(found) != 1:
        _fail(f"expected exactly 1 `repos:` element named <owner>/{repo} in fleet.yml, found {len(found)}")
    item = found[0]
    first = item.start_mark.line
    lead = text.split("\n")[first][: item.start_mark.column]
    if lead.strip() != "-":
        _fail(f"the {repo} element does not start its line with `- ` (got {lead!r})")
    return first, _last_line(item)


def split(text: str, repo: str = REPO) -> tuple[str, str]:
    """(fleet.yml without the element, the fragment holding it)."""
    first, last = element_span(text, repo)
    lines = text.splitlines(keepends=True)
    moved = "".join(lines[first:last + 1])
    rest = "".join(lines[:first] + lines[last + 1:])
    fragment = HEADER + "repos:\n" + moved

    before = yaml.safe_load(text)["repos"]
    want_rest = [r for r in before if not str(r.get("name", "")).split("/", 1)[-1] == repo]
    want_moved = [r for r in before if str(r.get("name", "")).split("/", 1)[-1] == repo]
    if yaml.safe_load(rest).get("repos") != want_rest:
        _fail("fleet.yml without the element does not parse to the other elements")
    if yaml.safe_load(fragment) != {"repos": want_moved}:
        _fail("the fragment does not parse to exactly the element")
    rest_doc = yaml.safe_load(rest)
    if {k: v for k, v in rest_doc.items() if k != "repos"} != {k: v for k, v in yaml.safe_load(text).items() if k != "repos"}:
        _fail("the cut changed something outside `repos:`")
    return rest, fragment


# The shipped tests load fleet.yml through rs.load_config; while the fragment
# exists, that load also appends its elements, so the tests hold the whole
# fleet (base plus evals) before and after /adopt-evals merges it.
TEST_LOADER = '''

# The adoption kit's DECISIONS C13: fleet.yml declares the base repos and
# fleet.evals.yml (until /adopt-evals merges it) skills-evals' element. While
# the fragment exists, loading the shipped fleet.yml appends its elements, so
# these tests hold the whole fleet; a repo declared in both is refused.
KIT_FLEET = Path(__file__).resolve().parent.parent / "repo-settings" / "fleet.yml"
KIT_FRAGMENT = KIT_FLEET.with_name("fleet.evals.yml")
_REAL_LOAD_CONFIG = rs.load_config


def _kit_load_config(path):
    cfg = _REAL_LOAD_CONFIG(path)
    if not KIT_FRAGMENT.is_file() or Path(path).resolve() != KIT_FLEET:
        return cfg
    extra = _REAL_LOAD_CONFIG(str(KIT_FRAGMENT)).get("repos") or []
    declared = {r.get("name") for r in cfg.get("repos") or []}
    both = sorted(r.get("name") for r in extra if r.get("name") in declared)
    if both:
        raise AssertionError(f"declared in both fleet.yml and fleet.evals.yml: {both}")
    return dict(cfg, repos=list(cfg.get("repos") or []) + list(extra))
'''

LOADER_START = '''
    loader = patch.object(rs, "load_config", _kit_load_config)
    loader.start()
    unittest.addModuleCleanup(loader.stop)
'''

FRAGMENT_TESTS = '''

class EvalsFragmentTests(unittest.TestCase):
    """fleet.yml alone is the base; fleet.evals.yml adds skills-evals
    (the adoption kit's DECISIONS C13)."""

    def _base(self):
        return _REAL_LOAD_CONFIG(str(KIT_FLEET))

    def _names(self, cfg):
        return [r["name"].split("/", 1)[-1] for r in cfg.get("repos") or []]

    def test_the_merged_fleet_declares_skills_evals_once(self):
        self.assertEqual(self._names(rs.load_config(str(KIT_FLEET))).count("skills-evals"), 1)

    @unittest.skipUnless(KIT_FRAGMENT.is_file(), "fleet.evals.yml is merged")
    def test_fleet_yml_alone_declares_no_skills_evals(self):
        self.assertNotIn("skills-evals", self._names(self._base()))

    @unittest.skipUnless(KIT_FRAGMENT.is_file(), "fleet.evals.yml is merged")
    def test_the_fragment_holds_only_skills_evals(self):
        frag = _REAL_LOAD_CONFIG(str(KIT_FRAGMENT))
        self.assertEqual(list(frag), ["repos"])
        self.assertEqual(self._names(frag), ["skills-evals"])

    @unittest.skipUnless(KIT_FRAGMENT.is_file(), "fleet.evals.yml is merged")
    def test_fleet_yml_alone_renders_with_only_the_guidance_sync_id(self):
        # repo-settings.yml's plan job on a setup without evals: the
        # ROSTER_WRITER_APP_ID variable is unset there.
        with patch.dict(os.environ, {"GUIDANCE_SYNC_APP_ID": "900001"}):
            os.environ.pop("ROSTER_WRITER_APP_ID", None)
            targets = rs.resolve_targets(self._base(), None)  # renders every body
            self.assertTrue(targets)
            for t in targets:
                eff = t["effective"]
                if eff.get("ruleset"):
                    rs.build_ruleset_body(eff["ruleset"])
                rs.build_extra_ruleset_bodies(eff)

    @unittest.skipUnless(KIT_FRAGMENT.is_file(), "fleet.evals.yml is merged")
    def test_the_merged_fleet_needs_the_roster_id(self):
        # The negative control for the test above: skills-evals' element names
        # the roster App, so the merged fleet does not even resolve without it
        # (resolve_targets renders every body).
        with patch.dict(os.environ, {"GUIDANCE_SYNC_APP_ID": "900001"}):
            os.environ.pop("ROSTER_WRITER_APP_ID", None)
            with self.assertRaises(rs.ConfigError) as cm:
                rs.resolve_targets(rs.load_config(str(KIT_FLEET)), None)
        self.assertIn("ROSTER_WRITER_APP_ID", str(cm.exception))

    def test_a_repo_declared_in_both_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            fleet, frag = Path(d).resolve() / "fleet.yml", Path(d).resolve() / "fleet.evals.yml"
            fleet.write_text('repos:\\n  - name: o/one\\n    manage: []\\n', encoding="utf-8")
            frag.write_text('repos:\\n  - name: o/two\\n    manage: []\\n', encoding="utf-8")
            with patch.dict(globals(), {"KIT_FLEET": fleet, "KIT_FRAGMENT": frag}):
                self.assertEqual(self._names(_kit_load_config(str(fleet))), ["one", "two"])
                frag.write_text('repos:\\n  - name: o/one\\n    manage: []\\n', encoding="utf-8")
                with self.assertRaises(AssertionError):
                    _kit_load_config(str(fleet))
'''

# One shipped test (kit_config.py's ENV_ID_TESTS) reads fleet.yml's text for
# the roster App's variable, which is in the fragment's element now.
TEST_EDITS = [
    ("""        text = (Path(__file__).resolve().parent.parent / "repo-settings" / "fleet.yml").read_text(encoding="utf-8")
        self.assertIn(\'actor_id: "${GUIDANCE_SYNC_APP_ID}"\', text)""",
     """        text = "".join(p.read_text(encoding="utf-8") for p in (KIT_FLEET, KIT_FRAGMENT) if p.is_file())
        self.assertIn(\'actor_id: "${GUIDANCE_SYNC_APP_ID}"\', text)"""),
]


def _once(text: str, old: str, new: str, where: str) -> str:
    n = text.count(old)
    if n != 1:
        _fail(f"{where}: expected 1 of {old[:70]!r}, found {n}")
    return text.replace(old, new)


def apply(root: Path, ctx) -> None:
    fleet = root / FLEET
    rest, fragment = split(fleet.read_text(encoding="utf-8"))
    fleet.write_text(rest, encoding="utf-8")
    (root / FRAGMENT).write_text(fragment, encoding="utf-8")

    tests = root / "tests" / "test_repo_settings.py"
    text = tests.read_text(encoding="utf-8")
    text = _once(text, "\n\ndef setUpModule():\n", TEST_LOADER + "\n\ndef setUpModule():\n", "tests/test_repo_settings.py")
    text = _once(text, "    unittest.addModuleCleanup(env.stop)\n",
                 "    unittest.addModuleCleanup(env.stop)\n" + LOADER_START.lstrip("\n"), "tests/test_repo_settings.py")
    for old, new in TEST_EDITS:
        text = _once(text, old, new, "tests/test_repo_settings.py")
    tests.write_text(text + FRAGMENT_TESTS, encoding="utf-8")
