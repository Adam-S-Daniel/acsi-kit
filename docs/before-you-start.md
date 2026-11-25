# Before you start

## What you need

| Need | Why |
|---|---|
| A paid Claude plan: Pro, Max 5x or Ultra | Every paid plan can run cloud sessions and scheduled tasks ([Anthropic's routines page](https://code.claude.com/docs/en/routines), read 2026-11-25). They draw on your plan's limits like any session. The kit's numbers were measured on Ultra (formerly Max 20x), so a smaller plan runs the same system more slowly. Set `CLAUDE_PLAN` and read [which plan](#which-plan) before you start. Nothing here has been tested on a Team plan. |
| Claude Code, current release | Needed for hooks, plugins, and skills. The eval harness doesn't pin the CLI, so it fails loudly when a release changes behavior. |
| A GitHub account, and optionally a second | The exports name two owners throughout ([one owner or two](#one-owner-or-two)). |
| A GitHub account on any plan, **Free included** | Set `PLAN=free` in `fleet.env` and every step works on a free account. A paid plan (Pro for a personal account, Team for an organization) only adds rulesets and environments on the three private repos and lets you make three more repos private. See [free or paid](#free-or-paid-github-plan). |
| One durable machine | The session miner, the waiting-on-you feed, and machine memory curation never run in the cloud. |
| git 2.54 or newer on that machine | Needed for config-based git hooks, which older git silently ignores. |
| `gh`, `git`, `jq`, `python3` with PyYAML, bash 4.4+ | The bootstrap scripts use them on Linux, WSL, or macOS. macOS ships bash 3.2, so install a current one (with Homebrew, for example) and run the scripts with it. The scripts avoid GNU-only flags, but the kit's test suites (`run-all-tests.sh`, `bootstrap/tests/`) run on Linux and assume GNU `sed` and coreutils. Sign `gh` in as the owner with `gh auth login`, run `gh auth refresh -s workflow` so a push can add workflow files, then run `gh auth setup-git`. |
| `node` and `npm` | Step 1's `add-content.sh` runs them to rebuild the generated guidance files, so the setup needs them from the start. `_agent-guidance`'s tests and the guidance improve lane use them too. |
| PowerShell 7 (Windows only) | Runs `wsl-automation`'s scheduled tasks. |

`bash bootstrap/preflight.sh` checks all of this on your machine, read-only, and prints the install command for your OS next to anything missing.

## With or without evals

The kit has two tracks. The **base** (`/adopt`) uses five repos and covers
the fleet guidance and its sync, the skills registries, repo settings as
code, the git-hook checks, each machine's install, and the routines that
keep guidance and memory current. **Evals** (`/adopt-evals`, now or later)
add a sixth repo, `skills-evals`, along with the eval runner routine, its
secrets, three more Apps, and the weekly loop that spends part of your
plan's allowance on evals.

Without evals, nothing measures, improves, or retires your skills and
guidance automatically. A change to a skill or rule is only as good as your
own review, and one that stops helping stays until you notice. The advice to
get Max and the eval budget below apply to evals. The base's routines still
draw on your plan's allowance, like any session.

## What it costs

- **Hands-on setup:** the [quick start](quick-start.md)'s 40 steps (27 base,
  13 evals) come to roughly one to two days. Two of the evals steps are
  optional. Most of the time goes to the browser steps (creating and
  installing six GitHub Apps, saving six routines) and to reviewing six
  starter pull requests. On GitHub Free it is five Apps, because
  `create-apps.sh` skips `settings-admin`: its key would live in an
  environment of the private `repo-settings`, and Free has none there.
- **Calendar time:** most of the rest is waiting on the eval budget, not
  work. `skills-evals`' `evals/budget.yml` gives all automated evals 30% of
  the weekly allowance (`weekly_cap: 0.30`) and reserves 0.0105 for one eval
  fire (`per_run_cap` plus `per_run_overrun`) until it is measured. An
  improve fire is charged about twelve eval fires at their measured mean, or
  that many full reservations before anything is measured. That leaves room
  for an improve fire in the first week, and for at least one fire of each
  kind every week. The weekly planner runs on Tuesdays at 07:00 UTC, after
  the allowance week turns over (Monday 17:00 UTC). An improve fire needs
  four fixtures for its skill, and a fixture the loop adds stays off the
  schedule until it has two clean runs. The kit's core skills ship with
  fixtures (`workflow-path-audit` has four), so the planner has something to
  run on day one, but your own skills need their own fixtures before they
  can get an improve fire. Expect the first improvement to be merged or
  rejected one to two weeks after the first eval runs.
- **Running it:** evals run as routines on your plan, so they draw down the
  weekly allowance like any session. They stay within the 30% cap, with a
  hard stop when the account meter reads 80% (`stop_when_account_above`).
  Review `evals/budget.yml` before the planner first runs. Its numbers are
  points of your own plan's week, and skills-evals scales its estimates by
  the `claude_plan` the kit sets ([which plan](#which-plan)). The fire API
  allows 30 fires an hour per routine and 100 an hour per account.

## Which plan

Set `CLAUDE_PLAN` in `fleet.env` to `pro`, `max5x`, or `ultra`. Ultra is
the plan Anthropic used to call Max 20x, and `max20x` still means it. It is
required because the kit's numbers come from the owner's Ultra account,
and a smaller plan has a smaller week. `copy-starter.sh` uses it to size the
`skills-evals` tree it copies (`bootstrap/lib/plan_sizing.py`), and
`create-environments.sh` uses it to set how often the fleet worker fires:

| `CLAUDE_PLAN` | `pro` ($20) | `max5x` ($100) | `ultra` ($200) |
|---|---|---|---|
| `claude_plan` in `evals/budget.yml` | `pro` | `max5x` | `ultra` |
| Allowance scale skills-evals applies (`ALLOWANCE_SCALE`) | 10 | 2 | 1 |
| `stop_when_session_above` (5-hour window) | `0.90` | `0.90` | not set |
| `judge_exclude_tiers` in `evals/roster-policy.yml` | `[fable, mythos]` | not set | not set |
| Fleet worker (`FLEET_WORKER_EVERY_HOURS` on `_agent-guidance`) | weekly (`168`) | every 12 hours | every 3 hours |
| Loop worker, with evals (`LOOP_WORKER_EVERY_HOURS` on `_agent-guidance`) | weekly (`168`) | daily (`24`) | daily (`24`) |
| Agent changelog watcher (you set its schedule, [routines](routines.md#agent-changelog-watcher)) | weekly | daily | daily |
| One week of the plan, in API-equivalent dollars (model) | about $140 ($120 to $280) | about $700 ($620 to $990) | about $1,400 ($1,200 to $1,700) |
| Base routines, a week | about $11 | about $51 | about $129 |
| Base routines, share of the week (model) | ~8% (4% to 9%) | ~7% (5% to 8%) | ~9% (8% to 10%) |
| Evals the weekly cap lets through, a week | about $37: about one pass over the core fixtures | about $190: five to six passes | about $370: about eleven passes |

The weekly cap (30%) and the 80% account stop stay as exported on every plan.

Why each setting differs:

- **`claude_plan` and the allowance scale.** The budget's numbers are
  fractions of your own plan's weekly allowance, so a Pro or Max 5x budget is
  in points of that smaller week. skills-evals prices a run from its token
  counts as if it ran on Ultra and multiplies by `ALLOWANCE_SCALE` for the
  budget's `claude_plan` (`harness/budget.py`): 10 on Pro and 2 on Max 5x,
  because Anthropic gives Ultra 10 times Pro's weekly allowance and Max 5x 5
  times. The kit sets only `claude_plan`; it no longer rewrites a per-plan
  rate. For calls recorded without token counts, `legacy_usd_per_point` (an
  exported $12.35 per Ultra point) stands in, divided by the same scale.
- **The 5-hour stop.** A sweep fires many runs in a few hours, which can use
  up a smaller plan's whole 5-hour window. Once the window reads 90%, no new
  fire starts, and a run already going stops taking on work. Pro and Max 5x
  have a 5-hour window; a verified Ultra account does not
  ([What is the Ultra plan?](https://support.claude.com/en/articles/17728952)),
  so Ultra sets no 5-hour stop. skills-evals' `harness/budget.py` checks
  `claude_plan` against the stop and fails, saying which key to fix, when a
  plan with a window has none.
- **Working hours (optional).** On Pro or Max 5x you can keep the loop from
  leaving you a nearly spent window when your day starts. Add a
  `working_hours` block to `evals/budget.yml` in your skills-evals repo, with
  `timezone` (an IANA name such as America/New_York), `days` (such as
  `[mon, tue, wed, thu, fri]`), `start` and `end` (such as `"09:00"` and
  `"18:00"`), and `session_stop` (such as `0.50`). From 5 hours before
  `start` until `end`, no fire starts and runs stop taking on work once the
  window reads `session_stop`. At other times the 90% stop applies. Without
  the block, the 90% stop applies at all hours.
- **The judge.** Pro bills Fable as usage credits from the first call, so
  the roster picks a judge from another tier.
- **The fleet worker.** One fire that took an issue cost $1.85. Every 3
  hours, that is 56 fires and about $104 a week, or three quarters of a Pro
  week at the middle estimate. Even daily it would take a tenth, which is
  still more than a smaller plan needs, so Pro
  fires it once a week, on Tuesday at 00:20 UTC, after the allowance week
  turns over.
- **The changelog watcher.** One fire cost $2.68, so running it daily costs
  about $19 a week, about a seventh of a Pro week at the middle estimate.
  A weekly run reads the week's vendor releases all at once.

### What the shares rest on

The dollar figures are the owner's, on Max 20x, measured on 2026-11-13 from
one fire of each routine: fleet worker $1.85, changelog watcher $2.68,
memory curation $4.54 (weekly), prompt-audit sweep $2.03 for its own session
(counted as one fire a week), and $0.87 for an eval fire (the mean of 304
fires since 2026-11-09, plus the routine session that runs it). One fire is
a thin sample, and a fleet worker fire that finds nothing to do costs less.

Two things are unknown, and each share's range covers both:

- **Dollars per point.** The exported `legacy_usd_per_point` of $12.35 is
  the low end of what was measured, which suits a guard because it
  overcharges rather than undercharges. Two controlled quiet nights
  (2026-11-19 and 2026-11-20) put the eval mix at $12.35 a point on Sonnet
  and $17.15 on Opus, and three whole weeks of the account's known spend come
  to at least $14, $17, and $20 a point. The middle estimate uses $14, and
  the range runs from $12.35 to $17. These are dollars per Ultra point; a
  point of a smaller plan's week costs them divided by the plan's scale.
- **How the plans' weeks compare.** Anthropic gives Ultra 10 times Pro's
  weekly allowance and Max 5x 5 times, which skills-evals turns into its
  scale of 10 for Pro and 2 for Max 5x. The worst end and the guard treat Max
  5x as half of Ultra's week and Pro as a tenth. The weekly hours Anthropic
  gave in 2025 (40 to 80, 140 to 280, and 240 to 480) would make them 0.58
  and a sixth, the favorable end of each range.

The figures also come from the owner's fleet of 16 repos, while the kit
starts you with 5, or 6 with `skills-evals`. Two routines grow with the repo
count, and neither has been measured across fleet sizes:

- **The fleet worker** lists pull requests and issues in every repo, which
  took about 25 of that fire's 79 tool calls. Based on those calls and each
  repo's share of the session's starting context, a repo adds $0.02 to $0.09
  a fire: $1.05 to $1.65 a fire for 6 repos, and $2.15 to $3.20 for 30. The
  open pull requests and issues it finds matter more than the repo count,
  since 44 of the 79 calls worked on specific items.
- **The prompt-audit sweep** audits each repo in a child session, which the
  $2.03 leaves out. One small repo's child cost $0.46, so a sweep is closer
  to $5 for 6 repos and $9 for 15.

At the kit's starting size the two roughly cancel out, so the table stands.
Each repo you add costs about $0.50 a week on Pro, under half a percent of the week at the
middle estimate, and a smaller share of a larger plan. A fleet of 30 repos
puts the base routines a quarter to two thirds above the table on the Max
plans, and more than doubles them on Pro.

The eval row is what the guard books at the legacy rate: 30% of the week is
$37, $190, or $370 of eval calls, compared with about $33 for one pass over
the 38 core fixtures. On the meter, that is 30% at worst and about 26% at
the middle estimate.

### On Pro and Max 5x

Both plans run the whole kit, just more slowly:

- **Max 5x.** The fleet worker fires twice a day, and evals cover the core
  fixtures about five times a week. At the worst end of the ranges, the base
  routines and evals together take about 40% of the week, so watch the meter
  during the first week.
- **Pro.** The fleet worker fires once a week, and evals cover the core
  fixtures about once a week. [What to set, and what to leave
  off](#on-pro-what-to-set-and-what-to-leave-off) is below.

### On Pro: what to set, and what to leave off

These are the settings that keep the kit inside a Pro week. "Every task on
this page" means every routine and scheduled task in [routines](routines.md).

- **`CLAUDE_PLAN=pro` in `fleet.env`.** It sets the eval budget in points of
  a Pro week, the 90% five-hour stop, no Fable judge, and a weekly fleet
  worker (see the [table above](#which-plan)).
- **`LOOP_WORKER_EVERY_HOURS=168`.** `create-environments.sh` sets it for you on Pro, and it only matters once you add evals.
- **Pick Sonnet on every task on this page.** When you save each scheduled
  task, choose Sonnet in its model selector instead of leaving the default.
  Claude Code's default model on Pro has been Opus since CLI v2.1.280
  ([model configuration](https://code.claude.com/docs/en/model-config), read
  2026-11-25). The eval mix measured $12.35 a point on Sonnet and $17.15 on
  Opus ([what the shares rest on](#what-the-shares-rest-on)). Never pick a
  Fable model ([Fable on your plan](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan),
  read 2026-11-25) or a 1M-context variant of a 4.6 model: on Pro they bill
  usage credits (the model configuration page, read 2026-11-25).
- **Check usage credits before the first routine runs.** Open
  [claude.ai/settings/usage](https://claude.ai/settings/usage). Either leave
  usage credits off or set a monthly cap you accept
  ([manage usage credits](https://support.claude.com/en/articles/12429409-manage-usage-credits-for-paid-claude-plans),
  read 2026-11-25). With credits off, a routine that reaches your limit is
  rejected until the window resets, which is the safe failure. With them on,
  it keeps running and bills the overage
  ([routines](https://code.claude.com/docs/en/routines), read 2026-11-25).
- **Schedule and leave off.** Schedule the changelog watcher weekly (`3 1 * * 1`),
  and keep the memory curation task on Sonnet. Leave the optional dashboard
  refresh off. [Article lift](routines.md#article-lift) is off by default:
  `create-environments.sh` sets `ARTICLE_WATCH_FEED_URL` to `none`, so each
  hourly run is skipped with a notice. Leave it that way.
- **Start with the base track only.** Add evals (`/adopt-evals`) after a
  week of watching the meter. At the worst end the base routines take 9% of
  a Pro week and evals another 30%.
- **What Pro changes about pace.** A weekly fleet worker takes at most three
  `agent-ready` issues a week, so press **Run now** on its routine when you
  want a pass sooner. Evals make about one pass over the core fixtures a
  week.
- **What is the same on every plan.** The limits are hourly: 100 scheduled
  runs per account, 30 API fires per task and 100 API fires per account.
  There is no daily cap, and a schedule can't run more often than hourly.
  Scheduled tasks are a research preview, so these limits may change
  ([routines](https://code.claude.com/docs/en/routines), read 2026-11-25).
  Cloud sessions count toward your plan's limits, with no separate charge
  for the cloud VM ([Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web),
  read 2026-11-25).

If the first week's meter shows the worst end, turn things off in this
order: first evals (the base works without `skills-evals`), then the fleet
worker (disable `fleet-worker-fire.yml` in `_agent-guidance` and press **Run
now** when you want a pass), and finally the changelog watcher.

## The config file

`fleet.env` is the only file you fill in. Start from
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
| `CLAUDE_PLAN` | `pro`, `max5x` or `ultra` (`max20x` is its old name): your Claude plan. Required. Sizes the eval budget and the fleet worker's schedule ([which plan](#which-plan)). |
| `REVIEWER` | Who approves `fleet-apply` and `plugin-runtime-review` (default `OWNER`). |
| `OWNER_NAME` | Fills `Example Adopter` and `<your name>` in public plugin manifests and notices (default `OWNER`). Letters, digits, spaces, `.` and `-` only (no apostrophe). Use a public handle, not your legal name, or the privacy check will flag it. |
| `VISIBILITY_AGENT_GUIDANCE`, `VISIBILITY_SKILLS_EVALS`, `VISIBILITY_WSL_AUTOMATION` | Paid plan only: `public` (default) or `private`. |
| `APP_NAME_PREFIX` | Apps are named `<prefix>-<app>` (default `OWNER` lowercased). App names are unique across GitHub, at most 34 characters. |
| `REPOS_DIR` | Where `install-machine.sh` keeps its clones (default `~/repos`). |
| `*_APP_ID` | Filled by `create-apps.sh`. |

**Never put a secret in `fleet.env`.** Private keys, client secrets,
bearers, and denylists go into GitHub secrets on stdin, through
`create-apps.sh` and `set-secrets.sh`. The scripts parse the file strictly
(it is never `source`d) and refuse an unknown key or malformed value.

Keep `fleet.env` and the `app-manifests/` folder that `create-apps.sh`
writes out of every repo you push. They hold no secrets, but they do hold
your App ids and names, and no repo needs them.

## One owner or two

The owner's fleet spans two GitHub accounts, so the exports name a second
owner wherever a workflow or registry lists the fleet: `_agent-guidance`'s
`SYNC_OWNERS`, `repo-settings.yml`'s per-owner token steps and matrix,
`fleet.yml`'s `example-site-b`, the git-hook installer's `includeIf` list,
and more. `copy-starter.sh` replaces the second owner's name with
`OWNER_TWO`, and refuses a tree that names that owner while `OWNER_TWO` is
empty.

- **Two accounts:** set `OWNER_TWO` to the second account. Install the three
  fleet-wide Apps there too (`create-apps.sh` makes them public for this and
  prints the steps), and run `apply-settings.sh --owner <OWNER_TWO>` signed
  in as that account.
- **One account:** set `OWNER_TWO` to the same login as `OWNER`. Before it
  fills in your name, `copy-starter.sh` removes the second owner from every
  YAML file (`lib/substitute.py`, which needs PyYAML for this step): the
  second token and plan steps, that owner's env keys, its matrix entry, and
  its word in `SYNC_OWNERS` and `OWNERS`. What remains names you once, so no
  workflow repeats a key or step id. Prose and scripts inside `run:` blocks
  keep their two-owner wording. A check for "either owner" still reads both
  tokens, which are now the same token, and `fleet.yml`'s `example-site-b`
  stays, under your login.

## Free or paid GitHub plan

You don't need a paid plan. Set `PLAN=free` if you are on GitHub Free, and
every step, including step 2's `create-repos.sh`, works. `create-repos.sh`
applies this from `PLAN`:

- **Free:** every repo is public except `acsi-agentskills-private`,
  `repo-settings`, and the optional `waiting-feed`. Those stay private and,
  on Free, unprotected: GitHub doesn't enforce rulesets there and offers no
  environments. The `fleet-apply` environment is skipped, so you run the
  settings apply from your own machine (`apply-settings.sh`) instead of
  through `repo-settings.yml`'s approved job. The engine logs the skip.
- **Paid:** the private repos get rulesets and environments too, and
  `_agent-guidance`, `skills-evals` and `wsl-automation` may be private.

GitHub Actions minutes are the other difference. These are estimates from the
shipped schedules, counting each job as at least one minute (estimated
2026-11-25, not measured). On Free, only private repos count against the 2,000
included minutes a month. Those are `repo-settings` (two daily workflows and
one weekly, about 65 minutes a month from schedules, and 120 to 200 with pull
requests) and `acsi-agentskills-private` (no scheduled workflow), so Free has
ample room. Standard-runner minutes in public repos are free. On a paid plan,
think before you make a repo private. `skills-evals`' schedules alone come to
roughly 4,500 to 4,700 minutes a month (two workflows run every 30 minutes and
one hourly), more than GitHub Pro's 3,000. `_agent-guidance` comes to roughly
1,500, or roughly 800 with `article-watch.yml` disabled.

## Where to work

Work from a copy of this kit outside any repo you push, with `fleet.env`
beside it. Run every quick start command from the kit's folder. Every script
takes `--dry-run`, which makes the same reads and prints each write instead
of making it, so use it first each time. Scripts are idempotent: a second
run prints `Nothing to change`.
