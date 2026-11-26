---
name: adopt-evals
description: Guide the user step by step through adding evals to this kit's system on their own GitHub account (the skills-evals repo, its loop's eval runner routine, its secrets and Apps, the eval fixture default, the optional federation, dashboard and explorer page), driven by bootstrap/status.sh --track evals, after checking the base is in place. From a fresh start it runs the base steps first, so it also sets up the whole system in one go. Use when the user types /adopt-evals, asks to add or continue setting up evals or the improvement loop, or wants the whole system including evals. For guidance and skills alone, use /adopt.
---

# Add evals, one step at a time

You are helping the user add evals to the system from this kit: the
`skills-evals` repo (the base never creates it), its eval runner routine,
the secrets and Apps it needs, and the loop that measures, improves, and
retires skills and guidance. `bootstrap/steps.json` puts each step on the
`base` or `evals` track. This skill runs the evals steps, and `/adopt`
(`.claude/skills/adopt/SKILL.md`) runs the base. Work from the kit's folder,
the one holding `bootstrap/`.

## The model and the session

Say what `/adopt`'s "The model and the session" says at the start of every
sitting: on Claude Pro (`CLAUDE_PLAN=pro` in `fleet.env`) the user types
`/model sonnet` first, because the default model on Pro is Opus, and each
sitting gets its own session (`claude`, then `/adopt-evals`).

On Pro, also say the Pro value at these steps
(`docs/before-you-start.md`, "On Pro: what to set and what to leave off"):

- **Steps 24 and 41** (the eval runner and the Loop worker): Sonnet in each
  task's model selector, picked explicitly. **Default** follows the
  account's default model, which Anthropic's model configuration page lists
  as Opus on Pro. Never a Fable model or a 1M-context variant of a 4.6
  model: on Pro those bill usage credits. Remove every connector the task's
  table in `docs/routines.md` doesn't name.
- **Step 32** (the dashboard and the explorer page) is optional: on Pro,
  leave the dashboard refresh off, and say so when status.sh lists the
  step. Article lift ships off too; leave it that way.
- **Step 41** (the Loop worker) again: its cadence,
  `LOOP_WORKER_EVERY_HOURS`, is already 168 on Pro, so it fires weekly at
  most. Nothing to choose.
- **The budget**: `CLAUDE_PLAN=pro` sizes `skills-evals`' eval budget in
  points of a Pro week, with no Fable judge.

## First: is the base in place?

1. Run `bash bootstrap/status.sh --track base` (with `--config <path>` if
   needed). Its last lines say `base: N of M done` and the next base step.
2. If a required base step is not done, the evals cannot work yet: the eval
   steps need the repos, the environments, the Apps and the applied
   settings the base sets up. Say so, then read
   `.claude/skills/adopt/SKILL.md` and follow it, from its "First sitting",
   until `bash bootstrap/status.sh --track base` reads
   `Next: nothing; every required base step is done`. Skip its last step
   (telling the user `/adopt-evals` comes later): you are already here.
   This is how a fresh start sets up the whole system in one command.
3. Once the base is done, say what evals cost before the first eval step:
   `docs/before-you-start.md`, "What it costs" and "With or without
   evals". Evals spend part of the plan's weekly allowance (the cap is in
   `skills-evals`' `evals/budget.yml`; help the user set their own numbers
   there in a pull request before the weekly planner first runs), and the
   first improvement lands one to two weeks after the first eval runs.

## Each turn

Follow `/adopt`'s "Each turn" section, with `--track evals` wherever it
says `--track base`: run `bash bootstrap/status.sh --track evals`, explain
the next step and link its `Read:` section, do it by its kind (dry run
first for a script), then close it by its check type. Only an **`ask`**
step is marked by hand: run `bash bootstrap/status.sh --mark <id>` once the
user says it is done. A `verify` step is never marked: status.sh refuses
`--mark` for it, so run `bash bootstrap/status.sh --track evals` again
until it reads done. The browser steps that create or install the eval
Apps (33, 34) and the federation step (26) are `verify` steps. Like an
`ask` step, step 34 takes `--mark 34` when verify.sh says gh's sign-in
cannot read the installations (HTTP 403): the user confirms them at
https://github.com/settings/installations first. Every evals
check reads only the evals track's part (`verify.sh --track evals`), so
the base stays done while you add `skills-evals`.

When status.sh reads `Next: nothing; every required evals step is done`,
run `bash bootstrap/verify.sh` for the whole setup and show its result.

## Steps with a catch

- **Step 40** (`regenerate.sh evals-fleet`) opens two pull requests: one in
  `repo-settings` (the `fleet.yml` element) and one in `_agent-guidance`,
  which adds `skills-evals` to `repos.yml` `cron_coverage.fleet`. The base
  leaves that name out, because the daily Dependabot health check fails on
  a repo that doesn't exist. The user merges both. Until then, an
  "Unclassified for cron coverage" issue naming `skills-evals` in
  `_agent-guidance` is expected (the drift report opens it once the repo
  exists and closes it after the merge).
- **The first evals steps**, in the order status.sh gives them, add
  `skills-evals` with the base's own scripts, which include it once it
  exists (`docs/evals-and-loop.md`, "Adding skills-evals"):
  `create-repos.sh skills-evals` (step 35), its starter pull request (36),
  the eval Apps (33, 34), the Loop worker routine (step 41), and only then
  `create-environments.sh` (step 37, which flips `EVALS_REPO`), followed by
  `regenerate.sh run-health-sha` and `actions-lock` (38),
  `regenerate.sh evals-fleet` (40) and `apply-settings.sh` (39). Never run
  `create-environments.sh` on the evals track before step 41, even when
  `create-apps.sh` ends by suggesting it.
- **Step 40** (`regenerate.sh evals-fleet`) declares `skills-evals` in
  `repo-settings/fleet.yml`. In a pull request on the user's
  `repo-settings`, it moves the element from `repo-settings/fleet.evals.yml`
  and deletes that file. The user merges it before step 39's apply. Once it
  is merged, `repo-settings.yml` also applies `skills-evals` on its own run,
  behind the `fleet-apply` approval.
- **Step 19** (eval.yml's default fixture): the shipped default runs as it
  is; a change is a pull request on the user's `skills-evals`.
- **Step 42** (each durable machine): `SKILLS_EVALS_URL` in
  `~/.config/wsl-automation/settings.env` goes from `none` to the user's
  `skills-evals` URL, which turns on the session miner and the usage census;
  then one `run-session-miner.sh --dry-run` by hand (docs/machine.md).
- **The Loop worker** (step 41, before step 37): the task (loop role,
  prompt in `docs/routines.md`) and its `LOOP_WORKER_FIRE_URL` and
  `LOOP_WORKER_FIRE_BEARER` on `_agent-guidance` (`create-environments.sh`
  already set `LOOP_WORKER_EVERY_HOURS` from `CLAUDE_PLAN`). It comes before
  step 37 because step 37's run of `create-environments.sh` flips
  `EVALS_REPO` to `<owner>/skills-evals`, after which a scheduled Loop worker
  fire runs and fails while its URL or bearer is unset.
- **The eval runner** (steps 24 and 25): the bearer is shown once. The user
  keeps it and the `trig_...` id and types both into
  `set-secrets.sh --only routine-fire` themselves.
- **Steps 26 and 32** are optional: offer them, and move on when the user
  declines.
- **Step 32** makes two claude.ai artifacts from one build
  (`docs/routines.md`, "Dashboard refresh"). Both start private; never turn
  on a public link for the user, it is their choice in claude.ai. An
  artifact can load only its own files (its content security policy allows
  only `'self'`), so the data travels with it:
  1. In a clone of `<you>/skills-evals`, run `npm ci` and `npm run check` in
     `explorer/` (all three pages match their source), and fetch the results
     branch: `git fetch origin persistent/eval-results` and
     `git show origin/persistent/eval-results:explorer/latest.json > <work>/latest.json`.
     No `latest.json` yet means `explorer-data.yml` has not run: wait for its
     first scheduled run, or dispatch it.
  2. The private build: a Dashboard artifact, as `dashboard/README.md`,
     "Adopting it", says. Its page is `dashboard/page/index.html`; its
     datasets are every entry of `dashboard/page/datasets.json`, including
     `explorer` (`dashboard/build.py` copies `explorer/latest.json` into
     it), with the user's owner and repo names in the live queries. Then
     run one refresh by hand and schedule `dashboard/tasks/refresh.md`
     every 2 hours.
  3. The public build: publish `explorer/dist/artifact/index.html` as an
     artifact, with `<work>/latest.json` published as a file named
     `latest.json` beside it (the Artifact tool's `publish` with
     `files: {"latest.json": "<work>/latest.json"}`). It reads that file,
     never GitHub. Both start private; if the user wants a public link, they
     turn it on from the artifact's Share menu. Refreshing it means
     republishing `latest.json`.
  4. Say what stays off: `evals/public-export.yml` ships
     `include_spend: false`, and `SITE_REPO` is required with no default:
     `create-environments.sh` set it from `fleet.env`, where `none` means no
     website and makes `site-sync.yml` and `site-freshness.yml` skip.
     `SITE_PAGE_URL`, `SITE_ASSET_URL` and `SITE_FRESHNESS_ROUTINE_ID` are
     needed only with a site (bootstrap/README.md, "Variables and secrets set
     by hand"). Changing either is the user's pull request, or `fleet.env`
     and `create-environments.sh` again.
- **Steps 33 and 34** (`create-apps.sh eval-improve roster registry-read`,
  then the installations): `create-apps.sh` wants the URL GitHub redirects
  to, so it runs in the user's own terminal. Step 34 also adds
  `skills-evals` to the three base Apps' installations.

## Never

- Never approve a deployment, an environment review or a pull request
  review, and never merge a pull request for the user. The
  `plugin-runtime-review` and `fleet-apply` approvals are the owner's alone.
- Never skip, weaken or edit a check, a ruleset or a test to make a step
  pass.
- Never mark a step done the user has not confirmed, and never mark one to
  move past a failure.
- Never print, paste or ask for a secret in the chat. `set-secrets.sh` and
  `create-apps.sh` read secrets from a hidden prompt, a file or a pipe; let
  the user type them there.
