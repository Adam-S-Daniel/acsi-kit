# Generated files and placeholders

The export rebuilt every generated file it could offline. A few need a
GitHub API, a commit that exists only after you push, or your own Apps, so
they arrive with a placeholder or the owner's value.
[`export/REGENERATE.md`](../export/REGENERATE.md) lists them.

`bootstrap/regenerate.sh <task>` rebuilds each one with the repo's own
tooling and proposes the result as a pull request on `regenerate/<task>`.
`--check` reads your default branches and says whether the task is done
(this is what `status.sh` asks), `--dry-run` changes nothing, and
`--track base` or `--track evals` limits a task to one track's repos. The
tasks are `skills-locks`, `hook-pin`, `run-health-sha`, `codex-pin`,
`actions-lock`, and, for evals, `evals-fleet`, which merges
`fleet.evals.yml` into `fleet.yml` ([the first
apply](settings-and-apps.md#the-first-apply)) and adds `skills-evals` to
`_agent-guidance`'s coverage list. Run these steps after you
merge the starter pull requests and before the first settings apply.

This table shows every item in `REGENERATE.md` and the quick start step that
handles it:

| Repo | Item | Step |
|---|---|---|
| `_agent-guidance` | `skills.lock` | 14 |
| `_agent-guidance` | `repos.yml` `skills_bootstrap.ref` | 15 |
| `_agent-guidance` | `.github/workflows/actions.lock` | 18 |
| `repo-settings` | `.github/workflows/scheduled-run-health.yml` | 16 |
| `repo-settings` | `skills.lock` | 14 |
| `repo-settings` | `.github/workflows/actions.lock` | 18 |
| `repo-settings` | GitHub App ids | 8, 37 |
| `repo-settings` | `repo-settings/fleet.yml`'s repo list | 9 |
| `repo-settings` | `repo-settings/fleet.evals.yml` | 40 |
| `wsl-automation` | `.github/workflows/scheduled-run-health.yml` | 16 |
| `wsl-automation` | `skills.lock` | 14 |
| `wsl-automation` | `.github/workflows/actions.lock` | 18 |
| `wsl-automation` | The Codex Cloud bootstrap pin | 17 |
| `wsl-automation` | The waiting feed's commit identity | 13 |
| `wsl-automation` | The Bash tasks' settings | 22 |
| `wsl-automation` | The waiting feed's repository | 2, 22 |
| `skills-evals` | `.github/workflows/scheduled-run-health.yml` | 38 |
| `skills-evals` | `.github/workflows/actions.lock` | 38 |
| `skills-evals` | The routine trigger id | 24, 25 |
| `skills-evals` | `.github/workflows/eval.yml` | 19 |
| `acsi-agentskills` | `skills.lock` | 14 |
| `acsi-agentskills-private` | `skills.lock` | 14 |
| `acsi-agentskills` | `.github/workflows/scheduled-run-health.yml` | 16 |
| `acsi-agentskills-private` | `.github/workflows/scheduled-run-health.yml` | 16 |
| `acsi-agentskills` | `.github/workflows/actions.lock` | 18 |
| `acsi-agentskills-private` | `.github/workflows/actions.lock` | 18 |
| `acsi-agentskills` | `<your name>` | 12 |
| `acsi-agentskills-private` | `<your name>` | 12 |
| `acsi-agentskills` | `scripts/cloud-env-setup.sh` `fleet_pin_commit` | 16 |
| `acsi-agentskills` | `.github/workflows/ci.yml`'s eval-protection gate checkout | 16 |

`REGENERATE.md` puts the two registries under one heading, but
`acsi-agentskills-private` has no `scheduled-run-health.yml`, so step 16
does nothing there. Step 2 creates the waiting feed's repository only with
`--with-optional`.

## The skills locks

`bash bootstrap/regenerate.sh skills-locks`, twice:

1. The first run finds forty zeros still pinned in `acsi-agentskills`'
   `skills.lock` and proposes the output of the registry's generator
   (`python3 scripts/generate_skills_lock.py`, which pins the registry's
   HEAD). Merge that pull request.
2. The second run checks that lock (`--check` and `--check-current`) and
   copies it into `acsi-agentskills-private`. It then re-pins
   `_agent-guidance`, `repo-settings`, and `wsl-automation` by running the
   registry's generator on a clone of your registry (`--repo`), keeping each
   lock's bundles. Merge the four pull requests.

Your registry starts with the core skills and the optional ones you added in
step 1, so each lock names those. The exported consumer locks name the
source registry's longer list until this step replaces them. After that,
`skills-lock-bump.yml` in `_agent-guidance` keeps the consumers current,
four times a day and whenever the registry changes.

## The skills-bootstrap hook pin

`_agent-guidance`'s `repos.yml` `skills_bootstrap.ref` names the registry
commit that the delivered `.claude/hooks/skills-bootstrap.sh` comes from.
The export already computed its `sha256` from the exported hook.
`bash bootstrap/regenerate.sh hook-pin` sets `ref` to your
`acsi-agentskills` HEAD after confirming that the hook there has exactly
that sha256. If the two copies have drifted, it refuses. In that case,
review the hook and run `_agent-guidance`'s `scripts/bump-hook-pin.sh`,
which re-pins both and opens its own pull request. The bumper runs it from
then on.

## The scheduled-run-health pin

`scheduled-run-health.yml` in `repo-settings`, `skills-evals`,
`acsi-agentskills`, and `wsl-automation` calls `_agent-guidance`'s reusable
workflow. A cross-repo reusable workflow needs a full sha, and the export
ships forty zeros. `bash bootstrap/regenerate.sh run-health-sha` writes your
`_agent-guidance` default branch's commit into each repo that exists: the
three base repos in step 16, and `skills-evals` once the evals track creates
it (step 38).

In `acsi-agentskills` the same pull request sets that commit in two more
places, which the export ships naming a commit of the source owner's
`_agent-guidance` that yours doesn't have:

- `fleet_pin_commit` in `scripts/cloud-env-setup.sh`. A cloud session
  downloads the fleet-guidance installer (`.claude/hooks/fleet-memory.sh`)
  from your `_agent-guidance` at that commit and checks it against
  `fleet_pin_sha256` on the next line. Until the commit is yours, the
  download fails and every cloud session prints
  `fleet-guidance: setup skipped`, so it starts without the guidance.
- The `ref` of the "Check out the eval-protection gate" step in
  `.github/workflows/ci.yml`. The step runs only on the evals track
  (`EVALS_REPO`), where it fails on every pull request until the ref is a
  commit of yours.

The task never writes `fleet_pin_sha256`: `copy-starter.sh` already set it
to the digest of the registry's own copy of the installer. Before it changes
anything, the task checks that your `_agent-guidance`'s copy at the new
commit has that digest. If it doesn't, the two repos came from different
versions of the kit, and the task stops and names both files. Run
`bootstrap/copy-starter.sh` for the repo on the older kit, merge its pull
request, and run the task again.

`--check` reports each part on its own line. Any commit of your
`_agent-guidance` counts as done, not only the newest, so a later bump of
either pin doesn't turn the step back to not done. To bump one later, use
the commands in the comments above `fleet_pin_commit`.

## The Codex Cloud pin

`wsl-automation`'s `scripts/sync-codex-cloud-environments.sh` holds two
pins, and both ship as placeholders that fail closed:

- `bootstrap_revision` and `bootstrap_sha256`: your registry's
  skills-bootstrap hook at a reviewed commit, and its digest. They ship as
  zeros (setup reports skills `DEGRADED`).
- `fleet_pin_commit` and `fleet_pin_sha256`: the fleet-guidance installer
  (`.claude/hooks/fleet-memory.sh`) in your `_agent-guidance` at a commit,
  and its digest. They ship as ones (setup fails).

`bash bootstrap/regenerate.sh codex-pin` sets the first pair to your
`acsi-agentskills` HEAD and its hook's sha256, and the second to your
`_agent-guidance` HEAD and the installer's sha256 there. It then runs the
script's own test with the new pins and proposes the change. `--check`
reports each pin on its own line. Skip the step if you do not use Codex.

`_agent-guidance`'s `docs/codex-cloud.md` shows the same guidance pin in a
block you paste into a Codex Cloud environment by hand. No task edits it: its
`fleet_pin_commit` ships as forty zeros, which fail closed, and its
`fleet_pin_sha256` already matches your installer. Before you paste the
block, set the commit to your `_agent-guidance`'s main commit
(`git rev-parse origin/main`), as its comment says.

## The action lockfiles

Every repo pins its actions through `.github/workflows/actions.lock`, with
an exact tag per `uses:`, each locked to a commit. The export changed only
the owner names, but confirm each file with the tool that writes it:

```bash
gh extension install github/gh-actions-lock
bash bootstrap/regenerate.sh actions-lock
```

This runs `gh actions-lock --no-narrow` in each repo and proposes any
change. `skills-evals` joins once it exists, when step 38 runs it again.
`--check` runs `gh actions-lock --verify`. Review an `actions.lock` diff as
you would a sha pin.

Each repo checks its lockfile on every pull request with the
[`verify-actions-lock`](https://github.com/Adam-S-Daniel/verify-actions-lock)
action, under the kit owner's name: from `agent-checks.yml` in
`_agent-guidance`, `repo-settings` and `acsi-agentskills-private`, and from
`ci.yml` in `acsi-agentskills`, `wsl-automation` and `skills-evals`. That
name stays as it is. It is a public action meant to be used directly, as you
use GitHub's own checkout action, so you don't need to copy or fork it. The export
keeps the name on purpose (rule C5 in
[`export/manifests/_common.yml`](../export/manifests/_common.yml)), and
`copy-starter.sh` replaces only the invented owners, so it never touches it.

So your CI runs a public action from the kit owner's account, the
`verify-actions-lock` linked above, at the tag each workflow names, and each
repo's `actions.lock` locks that tag to one commit, which the runner runs
even if the tag later moves. If you would rather run your own copy anyway,
fork it, change every `uses: Adam-S-Daniel/verify-actions-lock@<tag>` line
(the workflows above, and `ci.yml` in `_agent-guidance`) to your fork and a
tag of it, then run `gh actions-lock --no-narrow` in each repo and merge
those pull requests.

## Example repos in fleet.yml

The owner's fleet includes a site platform and two sites. So
`repo-settings/fleet.yml` declares `example-site-platform`,
`example-site-a`, and `<OWNER_TWO>/example-site-b`, and `_agent-guidance`'s
`repos.yml` lists them under `cron_coverage.fleet` and
`skills_bootstrap.repos`. Unless you have those repos, remove them in a pull
request on each repo before the first apply: the three `manage: ["labels"]`
rows in `fleet.yml`, and the three names in each of the two lists in
`repos.yml`. The tests read those files, so none of them needs an edit; they
pass with the example repos or without them, and with one owner or two.
`apply-settings.sh` refuses while `fleet.yml` names a repo that doesn't exist,
and a missing `cron_coverage.fleet` repo is an error for the coverage check.
Add your own consumers the same way later.

`cron_coverage.fleet` doesn't list `skills-evals`. The base track has no
such repo, and `dependabot-config-health.yml` fails every day while that
list names a repo neither owner has, which is also why the example names
have to go. When you add evals, `bootstrap/regenerate.sh evals-fleet` (step
40) adds `skills-evals` to the list in a pull request. If your
`_agent-guidance` came from an older copy of the kit and still lists
`skills-evals` without having the repo, remove that line. Step 11's check,
`bash bootstrap/verify.sh --only repos-yml`, reads both lists on your
default branch and names each repo neither owner has, the example repos and
such a `skills-evals` line alike, so the step reads done only once they are
gone.

The invented example repos appear in live config only in those places, in
`acsi-agentskills`' federated marketplace entry ([the
registry](skills.md#the-registry)), and in the eval runner's RULES line
([routines](routines.md#the-eval-runner)). `skills-evals` doesn't check them
out, pass them to the coverage census, or list them in
`harness/registries.yml`, which names only your two registries. The private
registry may be empty (`may_be_empty: true`), so the census runs on day one.

## The eval.yml fixture default

`skills-evals`' `.github/workflows/eval.yml` takes a `fixture` input. Its
default, `evals/workflow-path-audit/required-check-routing`, is a core
skill's fixture that ships with the kit, so a dispatch that keeps the
default will run. Keep it, or change it to one of your own fixtures in a
pull request, then mark the step done.

## Filled in by copy-starter.sh

Two items need no step of their own. `copy-starter.sh` replaces
`<your name>` in the plugin and marketplace manifests with `OWNER_NAME`. It
also replaces the waiting feed's placeholder commit identity, in
`scripts/publish-waiting-feed.sh` and its test, with your
`<id>+<login>@users.noreply.github.com` address, reading the id from GitHub.
