"""The skill gates pass the kit's first copy into a repo.

`bootstrap/copy-starter.sh` opens the registry's starter pull request against
a default branch that holds only the README the kit's `create-repos.sh`
wrote. With no skill at the merge-base, `scripts/check_skill_gates.py` read
every shipped skill as created and failed each one without a green
`with_skill` Eval line or a `create` entry in `docs/skill-impact.md` (five
failures on the real walk on GitHub Free, acsi-kit PR #139). A skill the
starter adds is not a change to judge: the adopter's later pull requests diff
against the merged starter, and the gates apply to them as before.

`run()` now passes, with a line saying why, when neither the merge-base nor
the base branch's tip has a SKILL.md or PURPOSE.md under `plugins/` or a
`docs/skill-impact.md`: a base with no registry at all. A base with either is
judged as before, and so is a branch cut from the README-only base before the
starter merged and opened after it. Tests in `scripts/test_check_skill_gates.py`
cover the first copy, a later edit on top of it (still a failure), a base
with only the impact file, and that stale branch.

Runs on the substituted tree.
"""

from __future__ import annotations

from pathlib import Path

GATE = (
    "    base_blobs, head_blobs = tree_blobs(point), tree_blobs(head)\n",
    "    base_blobs, head_blobs = tree_blobs(point), tree_blobs(head)\n"
    "    # The adoption kit's first copy: the base branch holds no registry at all\n"
    "    # (only the README the kit's create-repos.sh wrote), so this pull request\n"
    "    # adds every skill at once and there is no change to judge. Every later\n"
    "    # pull request diffs against the merged registry as usual. The base tip\n"
    "    # must be empty too: a branch cut before the starter merged and opened\n"
    "    # after it is judged.\n"
    "    if (not base_blobs and blob_id(point, IMPACT_FILE) is None\n"
    "            and not tree_blobs(base) and blob_id(base, IMPACT_FILE) is None):\n"
    "        return 0, [\"skill-gates: the base branch has no skills and no \"\n"
    "                   f\"{IMPACT_FILE} yet — this pull request adds the registry, \"\n"
    "                   \"so there is no change to judge\"]\n",
)

TESTS = (
    "def test_no_skill_change_passes(tmp_path):\n",
    '''def first_copy_repo(tmp_path: Path) -> Path:
    """The adoption kit's first copy: main holds only a README; `pr` adds a
    whole registry (two skills, the impact file with no entries)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _write(repo / "README.md", "# repo\\n")
    commit(repo, "readme")
    _git(repo, "checkout", "-q", "-b", "pr")
    for skill in (SKILL, OTHER):
        _write(skill_dir(repo, PLUGIN, skill) / "SKILL.md", f"# {skill}\\n\\nv1\\n")
    impact(repo)
    commit(repo, "starter")
    return repo


def test_first_copy_into_a_readme_only_repo_passes(tmp_path):
    repo = first_copy_repo(tmp_path)
    code, out = gate(repo)
    assert code == 0, out
    assert "the base branch has no skills and no docs/skill-impact.md yet" in out


def test_an_edit_after_the_first_copy_is_judged(tmp_path):
    repo = first_copy_repo(tmp_path)
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "-q", "--ff-only", "pr")
    _git(repo, "checkout", "-q", "-b", "next")
    edit_skill(repo)
    commit(repo)
    code, out = gate(repo, head="next")
    assert code == 1, out
    assert "no change to judge" not in out
    assert SKILL in out


def test_a_base_with_only_the_impact_file_is_judged(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    impact(repo)
    commit(repo, "impact only")
    _git(repo, "checkout", "-q", "-b", "pr")
    _write(skill_dir(repo, PLUGIN, SKILL) / "SKILL.md", f"# {SKILL}\\n\\nv1\\n")
    commit(repo)
    code, out = gate(repo)
    assert code == 1, out
    assert "no change to judge" not in out


def test_a_branch_cut_before_the_starter_merged_is_judged(tmp_path):
    repo = first_copy_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "stale", "main")
    _write(skill_dir(repo, PLUGIN, "late-skill") / "SKILL.md", "# late-skill\\n\\nv1\\n")
    commit(repo, "late")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "-q", "--ff-only", "pr")
    code, out = gate(repo, head="stale")
    assert code == 1, out
    assert "no change to judge" not in out
    assert "late-skill" in out


def test_no_skill_change_passes(tmp_path):
''',
)

EDITS = {
    "scripts/check_skill_gates.py": [GATE],
    "scripts/test_check_skill_gates.py": [TESTS],
}


def apply(root: Path, ctx) -> None:
    for rel, edits in EDITS.items():
        path = root / rel
        text = path.read_text(encoding="utf-8")
        for old, new in edits:
            n = text.count(old)
            if n != 1:
                raise SystemExit(f"first_starter_pr: expected 1 occurrence in {rel}, found {n}: {old[:70]!r}")
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
