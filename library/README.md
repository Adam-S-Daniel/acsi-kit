# The content library

This folder holds the kit's optional skills, guidance sections, and git
hooks: the **recommended** and **opinionated** tiers of
[`bootstrap/content-catalog.json`](../bootstrap/content-catalog.json). The
**core** items are already in [`starter/`](../starter/), and items the kit
doesn't ship are in neither place.

Nothing here is used until you choose it, either in the `/adopt` skill's
content step or by running
[`bootstrap/add-content.sh`](../bootstrap/add-content.sh) yourself:

```bash
bootstrap/add-content.sh --items recommended --dry-run   # see what would change
bootstrap/add-content.sh --items recommended,writing-adrs
```

It copies each chosen item into your copy of `starter/`, with everything
needed to test and measure it (its eval fixtures, eval-coverage row,
impact-log entry, and tests), and rebuilds the files generated from them.
Don't edit this folder by hand: `export/export.py` writes it, and
`export.py --check` compares it with a fresh export, like the starter trees.

## Layout

Each item has a folder, `<kind>/<id>/` (`skills/`, `guidance/`,
`git-hooks/`). Inside it is one folder per starter tree the item touches,
named after the starter folder (`agent-guidance`, `agent-skills`,
`skills-evals`):

| Path | What it is |
|---|---|
| `<tree>/files/<path>` | a file copied into `starter/<tree>/<path>` as it is (a skill's folder, its eval fixtures, a test module) |
| `<tree>/fragments/<name>` | a piece of text an op below inserts |
| `<tree>/ops.json` | `{"ops": [...]}`: the edits to files already in the tree |

## Ops

Each op names a `file` in the tree. Ops are idempotent: one that finds its
change already made does nothing, so a second `add-content.sh` run changes
nothing.

| `op` | What it does |
|---|---|
| `insert-section` | inserts the fragment, a `##` section, into `agents-md/base.md` after the first section in `follows` that is present (the headings that come before it in the source, nearest first), or before the first section |
| `coverage-row` | inserts the fragment, a row, into `agents-md/eval-coverage.yml` after the row of the first id in `follows` that is present; the section's `bytes` are recomputed afterwards |
| `impact-entry` | inserts the fragment before the first dated entry of an impact log (`docs/guidance-impact.md`, `docs/skill-impact.md`), or at its end when it has none |
| `insert-before` | inserts the fragment before `anchor`, which must occur once |
| `replace` | replaces `old` with `new`, which must occur `count` times (default 1) |
| `append-lines` | appends the fragment to the file, unless the file already holds it |
| `layout-skill` | adds `skill` to `plugin`'s list in `scripts/plugin_layout.json`, sorted, written in the file's canonical form |
| `insert-class` | adds the fragment, a top-level test class named `class`, to a Python file, before its `if __name__ == "__main__":` block (found by parsing the file); when the file already has a class of that name (the export keeps a class whose helpers other tests use), it adds the fragment class's methods that the file's class lacks |
| `insert-method` | adds the fragment, a method named `method`, at the end of class `class` (found by parsing the file) |
| `copy-if` | copies the fragment to `to` once every item in `requires` is installed (a test module that tests two items' fixtures) |

After the ops, `add-content.sh` rebuilds what is generated from the changed
files, as the export does: the fleet payload mirror
(`.claude/hooks/fleet-guidance.md`) and the agent-checks runner
(`.githooks/agent-checks`) in every starter tree, each tree's `AGENTS.md`,
the section byte counts, the registry's README table, and `skills.lock`,
including the private registry's copy.
