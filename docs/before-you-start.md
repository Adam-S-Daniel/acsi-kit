# Before you start

## What you need

| Need | Why |
|---|---|
| Claude Max, ideally Max 20x | Cloud sessions and routines (scheduled and API-triggered cloud runs) work on Pro too, but the routines and the eval budget draw on your plan's weekly allowance, and the kit's numbers are sized for Max 20x. See [which plan](#which-plan) before you start on Pro or Max 5x. Nothing here was tested on a Team plan. |
| Claude Code, current release | Hooks, plugins, skills. The eval harness pins nothing about the CLI and breaks loudly when a release changes behavior. |
| A GitHub account, and optionally a second | The exports name two owners throughout ([one owner or two](#one-owner-or-two)). |
| A GitHub plan you know | **Rulesets, required checks and environments are enforced on private repos only on a paid GitHub plan** (Pro for a personal account, Team for an organization). See [free or paid](#free-or-paid-github-plan). |
| One durable machine | Mining your own session transcripts, the waiting-on-you feed and machine memory curation never run in the cloud. |
| git 2.54 or newer on that machine | Config-based git hooks. Older git ignores them silently. |
| `gh`, `git`, `jq`, `python3` with PyYAML, bash 4.4+ | The bootstrap scripts use them, on Linux, WSL or macOS (where the system bash is 3.2: install a current one, e.g. with Homebrew, and run the scripts with it). They avoid GNU-only flags; the kit's own test suites (`run-all-tests.sh`, `bootstrap/tests/`) are run on Linux and assume GNU `sed` and coreutils. `gh` must be signed in as the owner (`gh auth login`, then `gh auth refresh -s workflow` so a push may add workflow files, and `gh auth setup-git`). |
| `node` and `npm` | `_agent-guidance`'s tests and the guidance improve lane. |
| PowerShell 7 (Windows only) | `wsl-automation`'s scheduled tasks. |

## With or without evals

The kit sets up two tracks. The **base** (`/adopt`) is the fleet guidance
and its sync, the skills registries, repo settings as code, the git-hook
checks, each machine's install and the routines that keep the guidance and
memory current, in five repos. **Evals** (`/adopt-evals`, now or later)
add the sixth repo, `skills-evals`, the eval runner routine, its secrets and
three more Apps, and the weekly loop in `skills-evals` that spends part of
your plan's allowance on evals.

Without evals you give up the measuring: your skills and guidance are never
measured, improved or retired automatically. A change to a skill or a rule
is only as good as your own review of it, and one that stops helping stays
until you notice. The advice to get Max and the eval budget below are about
evals; the base's routines still draw on your plan's allowance like any
session.

## What it costs

- **Hands-on setup:** the [quick start](quick-start.md)'s 35 steps (28 of
  them base, 7 evals) come to about 40 commands and browser actions,
  roughly one to two days. The
  browser steps (creating and installing six GitHub Apps, saving six
  routines) and reviewing six starter pull requests take most of it.
- **Calendar time:** most of the rest is waiting on the eval budget, not
  work. `skills-evals`' `evals/budget.yml` gives all automated evals 30% of
  the weekly allowance (`weekly_cap: 0.30`), and reserves 0.0105 for one
  eval fire (`per_run_cap` plus `per_run_overrun`) until it is measured. An
  improve fire is charged eight eval fires at their measured mean, or eight
  full reservations (0.084) while nothing is measured, so an improve fire
  can go in the first week, one of each kind a week at least. The weekly
  planner runs on Tuesdays at 07:00 UTC, after the
  allowance week turns over (Monday 17:00 UTC). An improve fire needs four
  fixtures for its skill, and a fixture the loop adds stays off the schedule
  until it has two clean runs. The kit's core skills ship with their fixtures
  (`workflow-path-audit` has four), so the planner has something to run on day one, but
  an improve fire for your own skills needs your own first. Expect the first improvement merged or
  rejected one to two weeks after the first eval runs.
- **Running it:** evals run as routines on your plan, so they draw down the
  weekly allowance like any session, within the 30% cap and with a hard stop
  when the account meter reads 80% (`stop_when_account_above`). Set your
  own numbers in `evals/budget.yml` before the planner first runs, above
  all `points_per_usd` ([which plan](#which-plan)). The fire
  API allows 30 fires an hour per routine and 100 an hour per account.

## Which plan

Set `CLAUDE_PLAN` in `fleet.env` to `pro`, `max5x` or `max20x`. It is
required, because the kit's numbers come from the owner's Max 20x account and
a smaller plan has a smaller week. From it, `copy-starter.sh` sizes the
`skills-evals` tree it copies (`bootstrap/lib/plan_sizing.py`) and
`create-environments.sh` sets how often the fleet worker fires:

| `CLAUDE_PLAN` | `pro` ($20) | `max5x` ($100) | `max20x` ($200) |
|---|---|---|---|
| `points_per_usd` in `evals/budget.yml` | `0.03` | `0.006` | `0.0015` (as exported) |
| `stop_when_session_above` (5-hour window) | `0.90` | `0.90` | not set |
| `judge_exclude_tiers` in `evals/roster-policy.yml` | `[fable, mythos]` | not set | not set |
| Fleet worker (`FLEET_WORKER_EVERY_HOURS` on `_agent-guidance`) | weekly (`168`) | every 12 hours | every 3 hours |
| Agent changelog watcher (you set its schedule, [routines](routines.md#agent-changelog-watcher)) | weekly | daily | daily |
| One week of the plan, in API-equivalent dollars (model) | about $50 ($33 to $280) | about $250 ($170 to $990) | about $1,000 ($670 to $1,700) |
| Base routines, a week | about $10 | about $50 | about $128 |
| Base routines, share of the week (model) | ~20% (4% to 30%) | ~20% (5% to 30%) | ~13% (8% to 19%) |
| Evals the weekly cap lets through, a week | about $10: a quarter of the core fixtures | about $50: each core fixture once | about $200: each core fixture four times |

The weekly cap (30%) and the 80% account stop stay as exported on every plan.

Why each one:

- **`points_per_usd`.** The budget charges each eval run its own dollar cost
  (the CLI's API-equivalent figure) times this rate. The exported `0.0015` is
  about $6.70 per point of the weekly meter, measured on Max 20x on
  2026-11-10 in quiet overnight windows when evals were the only use ($6 to
  $7.30). Left unchanged on a smaller plan, the guard would undercount evals
  4 or 20 times, and only the 80% account stop would hold them.
- **The 5-hour stop.** A sweep fires many runs in a few hours. On a smaller
  plan that can use up the whole 5-hour window, so a run stops starting work,
  and no fire starts, once the window reads 90%.
- **The judge.** Pro bills Fable as usage credits from the first call, so the
  roster picks the judge from another tier.
- **The fleet worker.** One fire that took an issue cost $1.85. At every 3
  hours that is 56 fires and about $104 a week: two Pro weeks at the middle
  estimate. Even daily it is a quarter of one, so Pro fires it once a week,
  on Tuesday at 00:20 UTC, after the allowance week turns over.
- **The changelog watcher.** One fire cost $2.68, so daily it is about $19 a
  week, more than a third of a Pro week at the middle estimate. Weekly, it
  reads a week of vendor releases in one run.

### What the shares rest on

The dollar figures are the owner's, on Max 20x, measured on 2026-11-13 from
one fire of each routine: fleet worker $1.85, changelog watcher $2.68,
memory curation $4.54 (weekly), prompt-audit sweep $2.03 for its own
session (counted as one fire every two weeks), and $0.87 for an eval fire (the mean of 304 fires
since 2026-11-09, plus the routine session that runs it). One fire is a
thin sample: a fleet worker fire that finds nothing to do costs less.

Two things are not known, and each share's range spans both:

- **Dollars per point.** The exported $6.70 is the low end of what was
  measured, which suits a guard: it charges evals too much, never too
  little. Over the 20 meter points that ticked in overnight windows from
  2026-10-26 to 2026-11-11 with evals running, eval calls cost $8.80 a point
  ($6.20 to $12.90 by night), and three whole weeks of the account's known
  spend come to at least $14, $17 and $20 a point. The middle estimate uses
  $10; the range runs from $6.70 to $17.
- **How the plans' weeks compare.** Anthropic publishes 5x and 20x for the
  5-hour window, not for the week. The middle estimate and the guard take
  Max 5x as a quarter of Max 20x's week and Pro as a twentieth. The weekly
  hours Anthropic gave in 2025 (40 to 80, 140 to 280 and 240 to 480) would
  make them 0.58 and a sixth, the favorable end of each range.

The figures also come from the owner's fleet of 13 repos, and the kit
starts you with 5, or 6 with `skills-evals`. Two routines grow with the
count, neither one measured across fleet sizes:

- **The fleet worker** lists pull requests and issues in every repo: about
  25 of that fire's 79 tool calls. By what those calls and each repo's share
  of the session's starting context can cost, a repo adds $0.02 to $0.09 a
  fire: $1.05 to $1.65 a fire for 6 repos, $2.15 to $3.20 for 30. The fire
  follows the open pull requests and issues it finds more than the count:
  44 of the 79 calls worked on specific items.
- **The prompt-audit sweep** audits each repo in a child session that the
  $2.03 leaves out. One small repo's child cost $0.46, so a sweep is nearer
  $5 for 6 repos and $9 for 15.

At the kit's starting size the two roughly cancel, so the table stands. Each
repo you add costs about $0.25 to $0.30 a week on Pro, half a percent of
the week at the middle estimate, and no larger a share of a larger plan's.
A fleet of 30 repos puts the base routines a fifth to four fifths above the
table.

The eval row is what the guard books, at its own rate: 30% of the week is
$10, $50 or $200 of eval calls, against about $42 for one pass over the 48
core fixtures. On the meter that is 30% at worst and about 20% at the
middle estimate.

### On Pro and Max 5x

Both run the whole kit, at a slower pace:

- **Max 5x.** The fleet worker fires twice a day, and evals cover the core
  fixtures about once a week. At the worst end of the ranges the base
  routines and evals together take 60% of the week, so watch the meter in
  the first week.
- **Pro.** The fleet worker fires once a week, and evals cover the core
  fixtures about once a month. Schedule the changelog watcher weekly, set
  the memory curation task's model to Sonnet (the owner's $4.54 fire ran on
  Opus), and leave the optional dashboard refresh off: one refresh cost the
  owner $7.59. At the worst end the base routines take 30% of the week
  and evals another 30%. A weekly fleet worker takes at most three
  `agent-ready` issues a week, so press **Run now** on its routine when you
  want a pass sooner.

If the first week's meter shows the worst end, turn things off in this
order: evals (the base setup works without `skills-evals`), then the fleet
worker (disable `fleet-worker-fire.yml` in `_agent-guidance` and press
**Run now** when you want a pass), then the changelog watcher.

## The config file

`fleet.env` is the one file you fill in. Start from
[`bootstrap/fleet.env.example`](../bootstrap/fleet.env.example):

```bash
cp bootstrap/fleet.env.example fleet.env
```

| Key | Meaning |
|---|---|
| `OWNER` | Your user or organization, exactly as in your clone URLs. Required. |
| `OWNER_TWO` | The second owner the exports name, or the same as `OWNER` ([one owner or two](#one-owner-or-two)). |
| `OWNER_TYPE` | `user` or `org` (default `user`). An org creates Apps under `organizations/<OWNER>/settings/apps`. |
| `PLAN` | `free` or `paid`. Required. |
| `CLAUDE_PLAN` | `pro`, `max5x` or `max20x`: your Claude plan. Required. Sizes the eval budget and the fleet worker's schedule ([which plan](#which-plan)). |
| `REVIEWER` | Who approves `fleet-apply` and `plugin-runtime-review` (default `OWNER`). |
| `OWNER_NAME` | Fills `Example Adopter` and `<your name>` in public plugin manifests and notices (default `OWNER`). Letters, digits, spaces, `.` and `-` only (no apostrophe). Use a public handle, never your legal name: the privacy check would trip on it. |
| `VISIBILITY_AGENT_GUIDANCE`, `VISIBILITY_SKILLS_EVALS`, `VISIBILITY_WSL_AUTOMATION` | Paid plan only: `public` (default) or `private`. |
| `APP_NAME_PREFIX` | Apps are named `<prefix>-<app>` (default `OWNER` lowercased). App names are unique across GitHub, at most 34 characters. |
| `REPOS_DIR` | Where `install-machine.sh` keeps its clones (default `~/repos`). |
| `*_APP_ID` | Filled by `create-apps.sh`. |

**Never put a secret in `fleet.env`.** No private key, client secret,
bearer or denylist: those go into GitHub secrets on stdin, through
`create-apps.sh` and `set-secrets.sh`. The scripts parse the file strictly
(it is never `source`d), and refuse an unknown key or a malformed value.

Keep `fleet.env` and the `app-manifests/` folder `create-apps.sh` writes out
of every repo you push. They hold no secret, but they hold your App ids and
names, and no repo needs them.

## One owner or two

The owner's fleet spans two GitHub accounts, so the exports name a second
owner everywhere a workflow or registry enumerates the fleet:
`_agent-guidance`'s `SYNC_OWNERS`, `repo-settings.yml`'s per-owner token
steps and matrix, `fleet.yml`'s `example-site-b`, the git-hook installer's
`includeIf` list, and more. `copy-starter.sh` replaces the second owner's
name with `OWNER_TWO`, and refuses a tree that names it while `OWNER_TWO` is
empty.

- **Two accounts:** set `OWNER_TWO` to the second. Install the three
  fleet-wide Apps there too (`create-apps.sh` makes them public for this,
  and prints the steps), and run `apply-settings.sh --owner <OWNER_TWO>`
  signed in as that account.
- **One account:** set `OWNER_TWO` to the same login as `OWNER`.
  `copy-starter.sh` then drops the second owner's legs from every YAML
  file before it fills in your name (`lib/substitute.py`, which parses each
  file and needs PyYAML for this step): the second token and plan steps,
  the second owner's env keys, its matrix entry, and its word in
  `SYNC_OWNERS` and `OWNERS`. What is left names you once, so no workflow
  repeats a key or a step id. Prose and scripts inside `run:` blocks keep
  their two-owner wording (a check for "either owner" still reads both
  tokens, which are now the same one); `fleet.yml`'s `example-site-b` keeps
  its entry under your login.

## Free or paid GitHub plan

`create-repos.sh` applies this from `PLAN`:

- **Free:** every repo is public except `acsi-agentskills-private`,
  `repo-settings` (and the optional `waiting-feed`), which are private and,
  on Free, unprotected: GitHub does not enforce rulesets there and offers no
  environments, so the `fleet-apply` environment is skipped and you run the
  settings apply from your own machine (`apply-settings.sh`) instead of
  through `repo-settings.yml`'s approved job. The engine logs the skip.
- **Paid:** the private repos get rulesets and environments too, and
  `_agent-guidance`, `skills-evals` and `wsl-automation` may be private.

## Where to work

Work from a copy of this kit outside any repo you push, with `fleet.env`
beside it. Every command in the quick start runs from the kit's folder.
Each script takes `--dry-run`, which makes the same reads and prints each
write instead; run it first every time. Each one is idempotent: a second
run prints `Nothing to change`.
