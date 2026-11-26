# Maintaining the kit

This page is for the kit's owner and the agents working on it. Adopters can
skip it.

## Re-pin

Each `export/manifests/*.yml` names a `source_sha`. The daily `resync` job
(`.github/workflows/resync.yml`, which you can also run from the Actions
tab) moves each one to its source's default-branch head
(`export/resync.py`), regenerates `starter/`, runs `export/tests`, and opens
or updates a single pull request from `resync/auto`. If a run finds every
source already at its pin, it closes any stale `resync/auto` pull request.

Before you merge that pull request:

- tier any new skill or guidance section in
  `bootstrap/content-catalog.json`; - record every departure in
  `export/DECISIONS.md`; - work through its "Pages to review" section
  (`export/doc_review.py`, using the page-to-source map in
  `export/doc-sources.yml`). Update each listed page, or say in the pull
  request why it needs no change.

The kit's CI runs no Windows Pester. When a re-pin changes a shipped
`.ps1` file or a Pester test, run them by hand on Windows: copy
`starter/wsl-automation` to a Windows folder, run `git init` there (the
line-endings test reads `git ls-files`), then run
`Invoke-Pester -Path .\tests`. It should report 0 failed.

When you add a page under `docs/`, add its sources to that map. Coverage
findings, meaning a routine spec or scheduled workflow that no page names,
only warn in `export/tests/test_doc_review.py`. Once `not_documented` is
settled, set `required: true` in the map to make them fail.

The job needs a GitHub App with contents and pull-requests write on this
repo. The repository variable `RESYNC_APP_CLIENT_ID` holds its client id,
and the repository secret `RESYNC_APP_PEM` holds its private key. Without
them, the job only writes what it would change to the run summary.

The job never re-pins `agentskills-private`, because that source is private,
and it doesn't rewrite `library/`. Do both by hand.

**Hold-back.** If a source's new head breaks the export or its tests,
`export/resync_holdback.py` keeps that source at its old pin while the
others move. It regenerates and tests the new pins together, then each moved
source alone. If each passes alone but they fail together, it holds all of
them back and no pull request opens. The pull request's summary has a "Held
back" section, and the job opens or updates the issue described under
"Failures" below, naming the held sources and the run, without failing. The
tail of the failing output goes to a file on the runner for the fix routine,
never into the issue or pull request, because this repo is public. A held
source needs an `edits` entry or patch that follows its change, and then it
re-pins on the next run.

**Fix routine.** A held source also fires a Claude cloud routine that
follows the change and pushes a `resync-fix/` branch
([`export/FIX-ROUTINE.md`](export/FIX-ROUTINE.md) is its guide). It fires at
most once per UTC day, and not while such a pull request is open and still
follows the held sources' heads. If a held source's head has moved past the
pins of the open one (it follows old heads), the re-sync closes it with a
comment and fires the routine again, still once per UTC day; closing needs the
re-sync App, and without one nothing fires. The
routine can push, but it can't open pull requests or comment, so
`.github/workflows/resync-fix-pr.yml` opens the pull request from the pushed
commit's message, labels it, and links it on the issue. Review and merge it
like any other.

The owner's fleet worker may also merge re-sync pull requests after its own
review, under the rule in the source spec's kit-only block, which the export
strips (`export/DECISIONS.md`, "Kit-only blocks in the source").

Two workflows keep the App key off the branch. `resync-fix-pushed.yml` runs
on the push, holds no secrets, and only announces it. `resync-fix-pr.yml`
runs on its `workflow_run`, which always uses the default branch's copy, so
a pushed branch can't change the workflow that holds the key.

Firing the routine needs the repository variable `RESYNC_FIXER_FIRE_URL` and
the Actions secret `RESYNC_FIXER_FIRE_BEARER`, both from the routine's API
trigger on claude.ai
([`export/FIX-ROUTINE-SETUP.md`](export/FIX-ROUTINE-SETUP.md) sets them up).
Without them, the step fails and names the missing one. The routine can't
run PowerShell, so a fix that touches a shipped `.ps1` asks for a Pester run
on Windows.

**Failures.** A failed run opens or updates a single issue, "Re-sync from
sources is failing", with the run's link and the failed step's name. Only a
run with nothing held back closes it, so watch for that issue rather than
the Actions tab. The fleet's daily scheduled-run health audit
(`.github/workflows/scheduled-run-health.yml`) also watches the job's
scheduled runs and files its own `ci` issue for the owner's fleet agents to
pick up (`_agent-guidance` lists this repo under `cron_coverage.fleet` in
its `repos.yml`).

**By hand.** As a fallback, check the sources out beside this clone and move
the shas. Run `npm ci` in the `_agent-guidance` checkout and in the
`skills-evals` checkout's `explorer/`, because two exports run that Node
code: `_agent-guidance`'s scripts and the esbuild build of `skills-evals`'
three explorer pages. Then run `python3 export/export.py` to rewrite
`starter/`, run `bash run-all-tests.sh` (as root,
`unshare --pid --fork --mount-proc -- bash run-all-tests.sh`), and record
every departure in `export/DECISIONS.md`.

## The plan table

The modeled rows of the "which plan" table in `docs/before-you-start.md`
come from `export/plan_shares.py`. Its inputs (dollars per fire, dollars per
meter point, and how the plans' weeks compare) sit at the top of the file,
with where each was measured. After changing an input, the eval budget, the
plan sizing, or the fleet worker's cadence, run
`python3 export/plan_shares.py --rows` and paste the rows.
`export/tests/test_plan_shares.py` fails until the table matches.

## Generated regions and held lists

The "Prompt, exactly" blocks in `docs/routines.md` sit between `generated:`
markers, and `export/doc_regions.py` writes them from their specs in
`starter/agent-guidance/`. After a spec changes, run
`python3 export/doc_regions.py --write` (`--check` only reports). The
re-sync pull request's `test` check fails until the page follows the source,
though the re-sync runs `--write` itself.

Two lists are maintained by hand: the agent-checks table in
`docs/guidance.md` and the by-hand variables in `docs/routines.md`.
`export/tests/test_doc_regions.py` fails when their items differ from the
runner's checks or `bootstrap/README.md`, and says which. Fix the page by
hand.

`export/tests/test_required_checks_table.py` fails when a repo's row in the
required-checks table of `docs/settings-and-apps.md` differs from what the
shipped `fleet.yml` requires, so the next source change to a repo's required
checks holds that source's re-sync back until the page follows.

## CI

`test` (`.github/workflows/ci.yml`) and `agent-checks` are the required
checks. `test` needs the `PRIVACY_DENYLIST` repository secret, with one
regular expression per line, and fails without it.

## Real GitHub Free walk

`export/real-free-walk/README.md` is the checklist for walking the base track
against real GitHub with a second, Free account, and `walk.sh` there is the
wrapper every command of that walk goes through: it runs in an isolated HOME
and refuses unless `gh` is signed in as the test account. Its settings file
names the test account, so it stays outside the repo.

## Outside pull requests

Outside pull requests never get that secret, so `test` always fails on them.
Read the change, bring it in on a branch of this repo, and close the outside
pull request with thanks.

## Issues

Issues are the feedback channel, and nothing here acts on one automatically.
Never give an issue template a label the owner's automation reads.

## Root files to avoid

Don't add `CLAUDE.md`, `AGENTS.md`, or `.claude/settings.json` at the root.
Adopters run Claude Code in their clone, so anything there would load into
their setup session.
