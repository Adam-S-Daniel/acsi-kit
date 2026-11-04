# Quick start

The easiest path is the guided one: clone this repo to a place outside any
other git repository (the [README](../README.md#start-here) says why), run
`claude` in the clone and type `/adopt`. It reads the real state of your account with
[`bootstrap/status.sh`](../bootstrap/status.sh), explains the next step and
runs each script with you, dry run first. To see where you are without it,
run `bash bootstrap/status.sh` yourself. The table below is the same list
([`bootstrap/steps.json`](../bootstrap/steps.json)).

Each step has a track. `/adopt` runs the **base** steps: guidance, the
skills registries, repo settings, git hooks, machines and the routines that
keep them. `/adopt-evals` adds the **evals** steps: the eval runner, its
secrets and Apps, and the loop that measures, improves and retires skills
and guidance. Run it later, or from the start for the whole system in one
command: it runs the base steps first. Without evals, nothing measures your
skills and guidance, and nothing improves or retires them automatically
([with or without evals](before-you-start.md#with-or-without-evals)). The
base never creates `skills-evals`: its first evals steps do
([adding skills-evals](evals-and-loop.md#adding-skills-evals)), and every
check runs on its own step's track, so the base reaches done without that
repo and adding evals later undoes no base step.

Every command runs from the kit's folder, with your config at `./fleet.env`.
`<you>` is your `OWNER`. Each script takes `--dry-run`; run it first every
time. Each is idempotent: a second run prints `Nothing to change`.

A starter pull request carries the export's whole tree, including workflows
that run as soon as it merges. Review it, above all `.github/workflows/`,
before you merge. Nothing is protected until step 20 applies `fleet.yml`, so
a check that cannot pass yet does not block a merge;
[merging the starter pull requests](settings-and-apps.md#merging-the-starter-pull-requests)
lists the failures to expect. Do not add collaborators before step 20.

<!-- quickstart:begin -->
<!-- generated from bootstrap/steps.json by bootstrap/render-quickstart.py: edit steps.json, then rerun it -->

| Step | What | Run | Time | Track | Read |
|---|---|---|---|---|---|
| 0 | Write fleet.env | `cp bootstrap/fleet.env.example fleet.env`, fill in `OWNER`, `OWNER_TWO` and `PLAN` | 5 min | base | [before you start](before-you-start.md#the-config-file) |
| 1 | Choose optional skills, guidance and git hooks | `bootstrap/add-content.sh --items recommended --dry-run`, then the same without `--dry-run` (or name the items you want, or `--items none`) | 10 min | base | [skills](skills.md#choosing-optional-content) |
| 2 | Create the five base repos | `bootstrap/create-repos.sh` (all but `skills-evals`, which only evals use: the evals track creates it) | 5 min | base | [settings](settings-and-apps.md#the-six-repos) |
| 3 | Store the privacy denylist | `bootstrap/set-secrets.sh --only privacy --denylist <file outside every repo>` | 10 min | base | [skills](skills.md#the-privacy-check) |
| 4 | Copy repo-settings and merge it | `bootstrap/copy-starter.sh starter/repo-settings <you>/repo-settings`, then review and merge the pull request | 20 min | base | [settings](settings-and-apps.md#merging-the-starter-pull-requests) |
| 5 | Create the environments | `bootstrap/create-environments.sh` (its `routine-fire` environment waits for the evals track's `skills-evals`) | 3 min | base | [settings](settings-and-apps.md#environments) |
| 6 | Create the three base GitHub Apps | `bootstrap/create-apps.sh guidance-sync settings-admin settings-read` (GitHub's App manifest flow, once per App, in the browser) | 20 min | base | [settings](settings-and-apps.md#github-apps) |
| 7 | Install the base Apps | Open each `https://github.com/apps/<slug>/installations/new` link `create-apps.sh` printed and pick the repos it names | 10 min | base | [settings](settings-and-apps.md#installing-the-apps) |
| 8 | Copy the App id into repo-settings | `bootstrap/create-environments.sh` again | 2 min | base | [settings](settings-and-apps.md#github-apps) |
| 9 | Drop the example repos from fleet.yml | In a pull request on `<you>/repo-settings`, remove the `example-site-*` entries from `repo-settings/fleet.yml` and their rows in `tests/test_repo_settings.py` (unless you have those repos) | 15 min | base | [settings](generated-files.md#example-repos-in-fleetyml) |
| 10 | Copy _agent-guidance and merge it | `bootstrap/copy-starter.sh starter/agent-guidance <you>/_agent-guidance`, then review and merge | 30 min | base | [guidance](guidance.md#what-_agent-guidance-holds) |
| 11 | Drop the example repos from repos.yml | In a pull request on `<you>/_agent-guidance`, remove the `example-site-*` names from `repos.yml` `cron_coverage.fleet` (unless you have those repos) | 10 min | base | [guidance](generated-files.md#example-repos-in-fleetyml) |
| 12 | Copy the two registries and merge them | `bootstrap/copy-starter.sh starter/agent-skills <you>/acsi-agentskills` and `bootstrap/copy-starter.sh starter/agent-skills-private <you>/acsi-agentskills-private`, then review and merge | 30 min | base | [skills](skills.md#the-registry) |
| 13 | Copy wsl-automation and merge it | `bootstrap/copy-starter.sh starter/wsl-automation <you>/wsl-automation`, then review and merge | 20 min | base | [machine](machine.md#scheduled-jobs-wsl-automation) |
| 14 | Pin every skills.lock to your registry | `bootstrap/regenerate.sh skills-locks`, merge, then run it again for the other four repos | 15 min | base | [generated files](generated-files.md#the-skills-locks) |
| 15 | Pin the skills-bootstrap hook | `bootstrap/regenerate.sh hook-pin`, then merge | 5 min | base | [generated files](generated-files.md#the-skills-bootstrap-hook-pin) |
| 16 | Pin the scheduled-run-health reusable | `bootstrap/regenerate.sh run-health-sha`, then merge the three pull requests | 5 min | base | [generated files](generated-files.md#the-scheduled-run-health-pin) |
| 17 | Pin the Codex Cloud bootstrap | `bootstrap/regenerate.sh codex-pin`, then merge | 5 min | base | [generated files](generated-files.md#the-codex-cloud-pin) |
| 18 | Regenerate the action lockfiles | `gh extension install github/gh-actions-lock`, then `bootstrap/regenerate.sh actions-lock` and merge what it opens | 10 min | base | [generated files](generated-files.md#the-action-lockfiles) |
| 20 | Apply fleet.yml: protect every repo | `bootstrap/apply-settings.sh` (and `--owner <OWNER_TWO>` signed in as that account; `fleet.yml` declares no `skills-evals` until the evals track adds it) | 5 min | base | [settings](settings-and-apps.md#the-first-apply) |
| 21 | Set up each durable machine | On each one: `bootstrap/install-machine.sh` (add `--with-codex` if you use Codex) | 15 min | base | [machine](machine.md#install-on-each-durable-machine) |
| 22 | Schedule the machine jobs | First, in the distro (or on Linux or macOS), copy your wsl-automation clone's `config/settings.env.example` to `~/.config/wsl-automation/settings.env` (every job, the session miner included, reads it) and check its repositories and `LESSONS_CLONE`; then Windows: `./scripts/register-tasks.ps1` in an elevated PowerShell 7, in your wsl-automation clone; Linux or macOS: `bash scripts/unix/install-schedule.sh <systemd\|launchd\|cron>` (its usage census, the Linux and macOS default, feeds only evals: without evals pass `--jobs session-miner`) | 30 min | base | [machine](machine.md#scheduled-jobs-wsl-automation) |
| 23 | Set up your cloud environments | At https://claude.ai/code, give each cloud environment the setup script from acsi-agentskills' `docs/multi-repo-delivery.md` and the network allowlist from _agent-guidance's `docs/reference/network-allowlist-claude-environments.txt` | 20 min | base | [machine](machine.md#cloud-environments) |
| 27 | Create the fleet worker routine | At https://claude.ai/code/routines: hourly at :20, the GitHub connector, the prompt in docs/routines.md | 15 min | base | [routines](routines.md#fleet-worker) |
| 28 | Create the prompt-audit sweep routine | At https://claude.ai/code/routines: API trigger only; store its fire URL and bearer on _agent-guidance as PROMPT_AUDIT_SWEEP_FIRE_URL (variable) and PROMPT_AUDIT_SWEEP_FIRE_BEARER (secret) | 15 min | base | [routines](routines.md#prompt-audit-sweep) |
| 29 | Create the agent changelog watcher routine | At https://claude.ai/code/routines: daily at 01:03 UTC, in an environment of its own with no variables | 20 min | base | [routines](routines.md#agent-changelog-watcher) |
| 30 | Schedule memory curation | A weekly task from a claude.ai project thread, and the same on each durable machine (docs/routines.md has both prompts) | 15 min | base | [routines](routines.md#memory-curation) |
| 31 | Create the guidance centralization audit routine | At https://claude.ai/code/routines: daily at 08:00 UTC, the GitHub connector, the prompt in _agent-guidance's `docs/routines/guidance-centralization.routine.md` | 20 min | base | [routines](routines.md#guidance-centralization-audit) |
| 35 | Create skills-evals | `bootstrap/create-repos.sh skills-evals` (with its labels and its `persistent/eval-results` branch) | 5 min | evals | [evals](evals-and-loop.md#adding-skills-evals) |
| 36 | Copy skills-evals and merge it | `bootstrap/copy-starter.sh starter/skills-evals <you>/skills-evals`, then review and merge | 20 min | evals | [evals](evals-and-loop.md#what-skills-evals-holds) |
| 33 | Create the three eval GitHub Apps | `bootstrap/create-apps.sh eval-improve roster registry-read` (GitHub's App manifest flow, once per App, in the browser) | 10 min | evals | [settings](settings-and-apps.md#github-apps) |
| 34 | Install the eval Apps | Open the `https://github.com/apps/<slug>/installations/new` link `create-apps.sh` printed for each and pick the repos it names; then add `skills-evals` to the installations of `guidance-sync`, `settings-admin` and `settings-read` | 10 min | evals | [settings](settings-and-apps.md#installing-the-apps) |
| 37 | Create its environment and copy the roster App's id | `bootstrap/create-environments.sh` again (the `routine-fire` environment in `skills-evals`, and `ROSTER_WRITER_APP_ID` in `repo-settings`) | 3 min | evals | [evals](settings-and-apps.md#environments) |
| 38 | Pin skills-evals' generated files | `bootstrap/regenerate.sh run-health-sha` and `bootstrap/regenerate.sh actions-lock` again, then merge what they open in `skills-evals` | 10 min | evals | [evals](evals-and-loop.md#adding-skills-evals) |
| 40 | Declare skills-evals in fleet.yml | `bootstrap/regenerate.sh evals-fleet`, then merge the pull request it opens in `repo-settings` (it moves `skills-evals`' element from `repo-settings/fleet.evals.yml` into `repo-settings/fleet.yml`) | 5 min | evals | [evals](evals-and-loop.md#adding-skills-evals) |
| 39 | Apply fleet.yml to skills-evals | `bootstrap/apply-settings.sh` again: it now includes `skills-evals` | 5 min | evals | [evals](settings-and-apps.md#the-first-apply) |
| 19 | Decide eval.yml's default fixture | `.github/workflows/eval.yml`'s `fixture` default, `evals/workflow-path-audit/required-check-routing`, ships with the kit and runs as it is: keep it, or change it to a fixture of your own in a pull request on `<you>/skills-evals` | 10 min | evals | [generated files](generated-files.md#the-evalyml-fixture-default) |
| 24 | Create the eval runner routine | At https://claude.ai/code/routines: an API-triggered routine with the prompt in skills-evals' `docs/routine/eval-runner-prompt.md`; keep the bearer it shows once and its `trig_...` id | 20 min | evals | [routines](routines.md#the-eval-runner) |
| 25 | Store the eval runner's bearer and trigger id | `bootstrap/set-secrets.sh --only routine-fire` | 5 min | evals | [routines](routines.md#the-eval-runner) |
| 26 | Optional: let eval.yml trade OIDC for an Anthropic token | In the Anthropic Console, set up workload identity federation for `skills-evals`, put its four ids in fleet.env, then `bootstrap/create-environments.sh` | 20 min | evals | [routines (optional)](evals-and-loop.md#workload-identity-federation) |
| 32 | Optional: the dashboard and the explorer page | Create two claude.ai artifacts: the private build as a Dashboard artifact (skills-evals' `dashboard/README.md`, Adopting it), refreshed every 2 hours, and the public build `explorer/dist/artifact/index.html` as an artifact with your `latest.json` beside it; both start private | 30 min | evals | [routines (optional)](routines.md#dashboard-refresh) |
| any | Check | `bootstrap/status.sh` for where you are; `bootstrap/verify.sh` for the fast checks, `--only settings` or `--only regen:<task>` for the slow ones | | | [quick start](#where-you-are) |
<!-- quickstart:end -->

## Where you are

`bash bootstrap/status.sh` prints one line per step: `done`, `next`, `todo`,
`optional`, or `asked: done`. Steps marked `files` or `verify` in
`steps.json` are checked against GitHub every time. Steps nothing can see
from here (an App installation is visible, but a routine saved at claude.ai,
a pasted setup script or another machine are not) are `ask` steps:

```bash
bash bootstrap/status.sh --mark 24     # after you saved the eval runner routine
bash bootstrap/status.sh --unmark 24   # if you marked it by mistake
```

Your answers live in a state file outside every repo
(`~/.local/state/adopt-the-whole-system/<owner>.json`).
`--track base` or `--track evals` lists one track's steps and picks the
next among them; every run also prints how many steps of each track are
done.

`bash bootstrap/verify.sh` checks the fast groups (repos, labels, branches,
environments, variables, Apps and their installations, secrets by name);
`--only settings` and `--only regen:<task>` clone repos to check the
settings engine's drift and the regenerated files. Without evals, its
`apps:` and `installs:` checks for `eval-improve` and `registry-read` and
its `values:routine-fire` check fail by design; `status.sh --track base`
is the base's check.
