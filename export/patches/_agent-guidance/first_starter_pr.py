"""The guidance touch gate passes the kit's first copy into a repo.

`bootstrap/copy-starter.sh` opens the starter pull request against a default
branch that holds only the README `create-repos.sh` wrote. There is no
guidance at the merge-base, so `scripts/check-guidance-touch.js` read every
section as a `create` and failed for want of an impact entry per section
(real walk on GitHub Free, acsi-kit PR #139). A section the starter adds is
not a change to judge: the adopter's later pull requests diff against the
merged starter and the gate applies to them as before.

The gate now passes, with a line saying why, when neither the merge-base nor
the base branch's tip has `agents-md/eval-coverage.yml` and the merge-base
has no `agents-md/base.md` either: a base with no guidance at all. Any base
that has either file is judged as the source judges it, so the B1
pre-manifest fallback is untouched. A test in `test/run-tests.sh` covers the
first copy and a later edit on top of it (still exit 1).

Runs on the substituted tree.
"""

from __future__ import annotations

from pathlib import Path

GATE = (
    "  const mergeBaseSha = gitMergeBase(repoRoot, baseSha, headSha);\n",
    "  const mergeBaseSha = gitMergeBase(repoRoot, baseSha, headSha);\n"
    "\n"
    "  // The adoption kit's first copy: the base branch holds no guidance at all\n"
    "  // (only the README the kit's create-repos.sh wrote), so this pull request\n"
    "  // adds the whole guidance tree and there is no change to judge. Every\n"
    "  // later pull request diffs against the merged tree as usual. A base with\n"
    "  // either file is judged below, which keeps B1's fallback as it is.\n"
    "  if (\n"
    "    gitShow(repoRoot, mergeBaseSha, \"agents-md/base.md\") === null &&\n"
    "    gitShow(repoRoot, mergeBaseSha, \"agents-md/eval-coverage.yml\") === null &&\n"
    "    gitShow(repoRoot, baseSha, \"agents-md/eval-coverage.yml\") === null\n"
    "  ) {\n"
    "    console.log(\n"
    "      \"check-guidance-touch: the base branch has no guidance yet (no agents-md/base.md or \" +\n"
    "        \"agents-md/eval-coverage.yml) — this pull request adds it all, so there is no change to judge\",\n"
    "    );\n"
    "    return;\n"
    "  }\n",
)

TEST = (
    "    assert_touch \"$event1\" \"$dir1\" 1 'section \"heading-one\" changed but has no new entry' \\\n"
    "        \"guidance touch: an edited extent with no entry fails, naming the id\"\n",
    "    assert_touch \"$event1\" \"$dir1\" 1 'section \"heading-one\" changed but has no new entry' \\\n"
    "        \"guidance touch: an edited extent with no entry fails, naming the id\"\n"
    "\n"
    "    # 1k. The adoption kit's first copy: the base holds only a README, the\n"
    "    #     head adds the whole guidance tree with no impact entries. Nothing\n"
    "    #     to judge (exit 0). An edit on top of that merged tree, with no\n"
    "    #     entry, still fails like case 1.\n"
    "    local dirk=\"$root/first_copy\" basek headk nextk eventk\n"
    "    rm -rf \"$dirk\"\n"
    "    mkdir -p \"$dirk/agents-md/sections\" \"$dirk/docs\"\n"
    "    git -C \"$dirk\" init -q >/dev/null\n"
    "    printf '# repo\\n' > \"$dirk/README.md\"\n"
    "    git -C \"$dirk\" -c user.name=test -c user.email=test@localhost add README.md\n"
    "    git -C \"$dirk\" -c user.name=test -c user.email=test@localhost commit -q -m readme\n"
    "    basek=$(git -C \"$dirk\" rev-parse HEAD)\n"
    "    printf '%s' \"$impact_stub\" > \"$dirk/docs/guidance-impact.md\"\n"
    "    headk=$(touch_commit \"$dirk\" starter \"$base_body\" \"$base_manifest\")\n"
    "    eventk=\"$TEST_DIR/touch-event-first-copy.json\"\n"
    "    write_event \"$basek\" \"$headk\" \"$eventk\"\n"
    "    assert_touch \"$eventk\" \"$dirk\" 0 'the base branch has no guidance yet' \\\n"
    "        \"guidance touch: the first copy into a README-only repo passes\"\n"
    "    nextk=$(touch_commit \"$dirk\" edit '## Heading One\n"
    "CHANGED body\n"
    "\n"
    "## Heading Two\n"
    "untouched body\n"
    "' \"$base_manifest\")\n"
    "    write_event \"$headk\" \"$nextk\" \"$eventk\"\n"
    "    assert_touch \"$eventk\" \"$dirk\" 1 'section \"heading-one\" changed but has no new entry' \\\n"
    "        \"guidance touch: an edit after the first copy is judged as usual\"\n",
)

EDITS = {
    "scripts/check-guidance-touch.js": [GATE],
    "test/run-tests.sh": [TEST],
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
