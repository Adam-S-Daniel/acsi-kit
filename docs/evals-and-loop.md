# Evals and the loop

## What skills-evals holds

[`skills-evals`](../starter/skills-evals/README.md) measures skills and
guidance sections and acts on the numbers:

- `harness/` runs an eval: `run_eval.py` loads a fixture, runs the agent
  with and without the subject (the skill, or a guidance section), scores
  each arm with scripted checks (`harness/scorers/objective.py`) and a judge model
  (`harness/scorers/judge.py`), and writes a summary.
- `evals/` holds the fixtures and the policy files: `budget.yml` (the
  allowance cap), `scheduled.yml` (which fixtures run on the weekly plan),
  `roster.yml` and `roster-policy.yml` (which models), `gate-policy.yml`
  (keeping and retiring), `removal-policy.yml` and `scope-policy.yml`
  (unused skills and paused evals), `improve-policy.yml` (whether accepted
  improvements merge on their own). The rules they set are written out in
  the generated [`docs/rules.md`](../starter/skills-evals/docs/rules.md):
  edit a YAML, run `python3 scripts/build_rules.py`, and CI fails while the
  page is stale.
- `scripts/` holds the planner (`plan_week.py`), the allowance guard, the
  gates, ingest, and the improve, draft, scaffold and retire lanes.
- `.github/workflows/` holds the workflows that fire the eval runner routine
  and turn what it pushes into pull requests.
- `explorer/` is the source of the three explorer pages, built with esbuild
  (`npm run build`): the public Evals Explorer for a website,
  `tool/index.html`; the same Explorer as a claude.ai artifact,
  `explorer/dist/artifact/index.html`; and the optional private project
  dashboard, `dashboard/page/index.html` (`dashboard/` holds its datasets,
  build and refresh tasks; [routines](routines.md#dashboard-refresh) says
  how to publish them).

The deepest account is its
[`docs/how-it-works.md`](../starter/skills-evals/docs/how-it-works.md);
[`DESIGN.md`](../starter/skills-evals/DESIGN.md) has the method.

## Adding skills-evals

The base never creates `skills-evals`: only the evals track needs it, and
on a base-only account its scheduled workflows would run with no routine to
fire. `/adopt-evals` adds it before any other evals step, with the same
scripts the base used, which include it once it exists:

1. `bootstrap/create-repos.sh skills-evals`: the repo, its labels and its
   `persistent/eval-results` branch (step 35).
2. `bootstrap/copy-starter.sh starter/skills-evals <you>/skills-evals`, then
   review and merge (step 36).
3. The three eval Apps, `eval-improve`, `roster` and `registry-read`
   (`create-apps.sh`, step 33), and their installations, with `skills-evals`
   added to the three base Apps' installations (step 34).
4. `bootstrap/create-environments.sh` again: the `routine-fire` environment
   and `repo-settings`' `ROSTER_WRITER_APP_ID` (step 37).
5. `bootstrap/regenerate.sh run-health-sha` and
   `bootstrap/regenerate.sh actions-lock` again, for `skills-evals`' copies
   (step 38).
6. `bootstrap/regenerate.sh evals-fleet`, then merge what it opens in
   `repo-settings` (step 40). The starter's `fleet.yml` declares only the
   base repos; `skills-evals`' element waits in
   `repo-settings/fleet.evals.yml`, which nothing applies. The task parses
   both files, appends that element to `fleet.yml`'s `repos:` list (one
   `fleet.yml` already declares is left as it is) and deletes the fragment,
   so a second run opens nothing.
7. `bootstrap/apply-settings.sh` again, which now protects `skills-evals`
   too (step 39).

Each of those checks reads only the evals track's part
(`verify.sh --track evals`), so the base steps stay done throughout.

## Fixtures

A fixture is a directory with a `fixture.yaml` (the prompt, the arms, the
objective checks, the judge rubric) and a `seed/` the agent starts from. The
kit ships the fixtures that test the machinery: `evals/guidance/_delivery`
(guidance delivery), `evals/guidance-bridge-canary`, `evals/propagation`,
the orchestrator scenarios, and test-only fixtures under `test/fixtures/`;
and the fixtures of the core skills and guidance sections (`evals/<skill>/`,
`evals/guidance/<section>/`). `evals/scheduled.yml` starts with a row for
each core item's fixture, so the weekly plan has something to run;
`bootstrap/add-content.sh` adds each optional item's fixtures and rows with
it ([choosing optional content](skills.md#choosing-optional-content)). Add
the rest as you write them: write a fixture for your
next skill under `evals/<skill>/<name>/`, run it locally
(`python3 harness/run_eval.py evals/<skill>/<name> --arm both --registry ../acsi-agentskills`, see the
[README's "Running"](../starter/skills-evals/README.md#running)), and add it
to `scheduled.yml` in a pull request. An improve fire needs four fixtures
for its skill.

The loop also asks for fixtures: the weekly plan files `needs-fixtures` and
`needs-harder-fixtures` issues, the fleet worker builds each one from real
merged work in your fleet, and a draft is promoted onto the schedule after
two clean ingested runs (`routine-fixture-supply.yml`, daily). The older
lane that mined merged pull requests in the routine is paused; its gate
stays in the table below.

## The eval runner and its lanes

Evals run inside a Claude routine on your plan, not on API dollars
([ADR 0010](../starter/skills-evals/docs/decisions/0010-run-ai-eval-steps-in-a-routine-fired-by-actions.md)).
`routine-eval-fire.yml` is the only workflow that fires it: it validates
the dispatch, runs the allowance guard, and POSTs to the routine's API
trigger with the bearer and trigger id from the `routine-fire` environment
([routines](routines.md#the-eval-runner)). The routine does the AI work in
its own sandbox and pushes the result to a branch of `skills-evals`; one
no-permission workflow per lane listens for it, and a gate workflow that
runs only the default branch's copy validates the branch without running
it and acts:

| Lane | Branch | The gate |
|---|---|---|
| eval results | `claude/eval-*` (files under `eval-results/`) | `routine-eval-ingest.yml` writes `routine-results/<run id>/` to `persistent/eval-results` |
| improve | `claude/eval-improve-*` (`eval-improve/`) | `routine-improve-gate.yml` opens a pull request in `acsi-agentskills` from `eval-improve/<skill>` with the `eval-improve` App |
| guidance improve | `claude/eval-guidance-improve-*` (`eval-guidance-improve/`) | `routine-guidance-improve-gate.yml` opens one in `_agent-guidance` |
| scaffold (paused: nothing fires it) | `claude/scaffold-*` | `routine-scaffold-gate.yml` opens a fixtures pull request here with the `roster` App |
| improve cost | `claude/eval-cost-*` (`improve-cost/`) | `routine-eval-ingest.yml` validates the cost record of an improve or guidance-improve run |
| draft skill | `claude/draft-skill-*` (`draft-skill/`, `evals/`) | `routine-draft-skill-gate.yml` opens a skill pull request in `acsi-agentskills` and a fixtures one here, or a hook-proposal issue |
| weekly spend | `claude/spend-*` (`spend/`) | `routine-eval-ingest.yml` validates `spend/weekly.json` and writes it to `persistent/eval-results`. This lane is the private dashboard refresh's (`dashboard/build.py --spend`), not the routine's; the public document carries it only with `include_spend: true` |

An improve or cost branch also matches `claude/eval-*`; the lanes' path
filters are disjoint, and the results lane excludes cost branches, so only
one fires. `skills-evals`'
[`docs/workflows.md`](../starter/skills-evals/docs/workflows.md) has the full
workflow table.

Other loop pull requests come from workflows, not from a routine branch:
`retire-skill/<skill>` and `retire-guidance/<section>` removals,
`eval-scope/<run id>` (evals paused or resumed), `fixture-promotion/<run id>`
and the `roster/proposal` roster change.

## Workload identity federation

Optional. `eval.yml`, the dispatch-only workflow that runs one fixture on
GitHub's runners instead of in the routine, pays with API credit: each leg
trades the runner's GitHub OIDC token for a short-lived Anthropic access
token (an RFC 7523 jwt-bearer exchange), so no API key is stored anywhere.
Skip this section if you run evals only through the routine.

1. In the Anthropic Console, create a workspace for these runs and give it
   a spend limit: that limit, not the workflow, is the hard ceiling.
2. Create a service account with access to that workspace.
3. Create a workload identity federation rule for that service account
   that trusts GitHub's issuer, `https://token.actions.githubusercontent.com`,
   with audience `https://api.anthropic.com` and subject
   `repo:<you>/skills-evals:ref:refs/heads/main`, so only the default
   branch gets a token. The Console's own federation docs have the current
   screens.
4. Put the four ids in `fleet.env`: `ANTHROPIC_FEDERATION_RULE_ID`
   (`fdrl_...`), `ANTHROPIC_ORGANIZATION_ID` (a uuid),
   `ANTHROPIC_SERVICE_ACCOUNT_ID` (`svac_...`) and `ANTHROPIC_WORKSPACE_ID`
   (`wrkspc_...`). They are ids, not secrets, but they name your account,
   so they live in repository variables rather than in the workflow file.
5. Run `bootstrap/create-environments.sh`: it sets them as `skills-evals`
   repository variables. `bootstrap/verify.sh --only federation` checks them.

Left unset, nothing fails on a schedule: the weekly `roster-refresh.yml`
dispatch (`roster_only`) skips the exchange with a notice and publishes no
roster. An eval leg does need the token, so a dispatched eval fails naming
the first unset variable. With any of the four set, the workflow checks
each value's shape before the exchange and fails with the variable's name
when one is missing or malformed. A failed exchange logs its HTTP status
and the error type only, never the response body.

## The budget

`evals/budget.yml` caps all automated evals at 30% of the weekly allowance,
one run at 0.01 plus a 0.0005 overrun, and stops a run when the account
meter reads 80%. Each run is charged its own dollar cost times
`points_per_usd`, which ships sized for Max 20x: set it for your plan first
([which plan](before-you-start.md#which-plan)). Three layers enforce it: the
in-run stop in the harness, the pre-fire check (`scripts/allowance_guard.py`,
which refuses a fire that would not fit and refuses when the GitHub API cannot
be read), and the weekly plan, which spends only the room left.
[What it costs](before-you-start.md#what-it-costs) turns these into calendar
time.

An improve fire is charged about twelve eval fires at their measured mean
(`IMPROVE_FIRE_UNITS` in `scripts/allowance_guard.py`), or that many full
reservations before any run is measured, and the improve cap allows at least
one fire of each kind a week. So an improve fire can go in
the first week; a refused one later in a week usually means the cap's share
is used.

## The loop

- **The weekly plan** (`routine-eval-weekly.yml`, Tuesdays 07:00 UTC, and
  again after every ingest to spend the room a finished run freed):
  `plan_week.py` computes the retirement verdicts, then plans eval fires
  and improve fires by band (a skill with a removal open first, then missing
  evidence, cells near a decision, the guidance sections nearest a verdict,
  improvements ranked by expected value per allowance point, then re-checks)
  within the room left, and dispatches them one at a time.
- **The usage census** from your machine
  ([machines](machine.md#scheduled-jobs-wsl-automation)) feeds all of it:
  which models the roster runs (`roster-refresh.yml`, Mondays), which skills
  the plan favors, and which skills nobody uses. Without a current census
  the roster falls back to the newest model per tier, and nothing is paused
  or removed for lack of use.
- **Improve:** an improve fire runs the skill-creator loop on one skill
  against a fixed holdout; an accepted candidate becomes a pull request.
  `improve-policy.yml`'s `improve_merge_mode: auto` makes it ready with
  auto-merge; `draft` leaves it for you. Even on `auto`, a change the
  registry's plugin runtime review would hold opens as a draft, and one that
  would fail its one-way-door check opens an issue instead.
- **Pause:** `eval-scope.yml` runs after every ingest and daily. It pauses
  the scheduled fixtures of a skill with no recorded use, of a fixture the
  bare model already passes, and of a removed skill, and resumes them, in an
  `eval-scope/<run id>` pull request that merges on its own.
- **Retire:** every day `skill-coverage.yml` computes each skill's verdict;
  a `retire` verdict gets a removal pull request (`retirement_mode: auto`),
  or an issue. The pull request merges only after a fresh-context agent has
  reviewed it and written `Adversarial-review: pass` into its body; any
  other result leaves it open for you. A skill nobody has used is removed
  the same way. When a verdict is `retire`, when an unused skill goes, and
  which removals file an issue instead (for you, or for the fleet worker),
  is in the generated
  [`docs/rules.md`](../starter/skills-evals/docs/rules.md). The
  core items listed in `evals/retirement-exempt.yml` are never retired: their
  verdict reads `retire-exempt` and nothing is opened.
- **New skills:** `routine-draft-skill.yml` picks one proposal a day, hooks
  first, from the new-skill lessons on `acsi-agentskills-private`'s
  `persistent/lessons` and from the `skill-proposal` issues you file in
  `acsi-agentskills` (with a "Skill name:" line).
- **New fixtures:** `routine-fixture-supply.yml`, daily.
- **Guidance waits for its window:** an accepted guidance improvement opens
  without auto-merge, and `guidance-merge-window.yml` arms it on Monday
  between 17:00 and 19:00 UTC; a guidance removal opens only then
  ([guidance](guidance.md#the-sync)).

These pull requests merge by auto-merge once required checks pass, with no
human review, within the limits `acsi-agentskills`'
[ADR 0021](../starter/agent-skills/docs/decisions/0021-automated-skill-changes-merge-without-review.md)
writes down. To review each one first, set `improve_merge_mode: draft` in
`evals/improve-policy.yml` and `retirement_mode: proposal` in both blocks
(`skills` and `guidance`) of `evals/gate-policy.yml`.

## Where results land

`persistent/eval-results` in `skills-evals` holds every ingested run, the
verdicts, the coverage census and the usage census your machine publishes;
it is never deleted (a deletion-only
ruleset guards it). The weekly plan's ranking is the run's
`improve-ranking` artifact.
