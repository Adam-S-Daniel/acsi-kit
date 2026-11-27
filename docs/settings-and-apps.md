# Settings, environments and Apps

## The six repos

The kit exports six repos. Under `OWNER`, `bootstrap/create-repos.sh`
creates the five the base needs: `_agent-guidance`, `repo-settings`,
`acsi-agentskills`, `acsi-agentskills-private`, and `wsl-automation`. It
creates the sixth, `skills-evals`, only when you name it
(`create-repos.sh skills-evals`, the first evals step, which `/adopt-evals`
runs). [Free or paid](before-you-start.md#free-or-paid-github-plan) decides
which are private.

Each repo gets a first commit, a generated README that `copy-starter.sh`
later replaces. The script also creates the three labels no settings file
declares: `agent-ready` (the fleet worker's queue), `on-hold` (paused by
you, and only you add or remove it) and `ci` (the label the scheduled
workflows file their issues under; creating an issue with a label the repo
lacks fails, so a first nudge would otherwise turn its run red).

In `skills-evals`, it creates the branch `persistent/eval-results` as an
orphan commit holding only a README. The weekly plan, the ingest, the
fixture supply, and both censuses all fetch that branch, none of them
creates it, and they fail on a new account without it.
`verify.sh --only branches` checks it. The script or routine that writes
each other `persistent/*` branch creates that branch. Once `skills-evals`
exists, a plain `create-repos.sh` checks it too. `--with-optional` also
creates `waiting-feed`, the private repo the waiting-on-you feed publishes
to ([machines](machine.md#scheduled-jobs-wsl-automation)).

`repo-settings` handles every other setting.

## Repo settings as code

`repo-settings/fleet.yml` in your `repo-settings` repo describes the desired
state of every repo, and `scripts/repo_settings.py` applies it ([its
README](../starter/repo-settings/README.md) has the full list). By default,
every repo gets:

- merge commits only (squash and rebase off), auto-merge on, branches
  deleted on merge;
- Actions: pinned actions required (a full SHA, or a tag an `actions.lock`
  pins), a read-only default token that cannot approve pull requests,
  approval for every outside contributor's fork run;
- Dependabot alerts and security updates, secret scanning with push
  protection, and CodeQL default setup;
- the label `agent-authored`;
- the ruleset "default branch protection": a pull request for every change,
  merge commits only, the required check `agent-checks`, admin bypass, and
  the `guidance-sync` App as the only bypass actor, so the sync can push.
  `repo-settings` itself is stricter. It has no App bypass, and an admin can
  bypass only by merging a pull request, because a direct push there would
  apply settings to the whole fleet with no checks. The sync reaches it
  through a pull request with auto-merge.

On `PLAN=free`, GitHub doesn't enforce rulesets on private repos, so
`repo-settings` and `acsi-agentskills-private` stay unprotected ([free or
paid](before-you-start.md#free-or-paid-github-plan)).

Each repo adds its own required checks, using the job names its workflows
actually publish:

| Repo | Required checks |
|---|---|
| `acsi-agentskills` | `pytest`, `pytest-windows`, `plugin-runtime-approval`, `agent-checks`, `merge-gate` |
| `skills-evals` | `test`, `agent-checks` |
| `_agent-guidance` | `test`, `agent-checks` |
| `wsl-automation` | `shell`, `test`, `test-linux`, `agent-checks` |
| `repo-settings` | `agent-checks`, `unit` |
| `acsi-agentskills-private` | `agent-checks` |

Each repo's `agent-checks` also runs the privacy scan with the
`PRIVACY_DENYLIST` secret (step 3) and only warns where the secret is
missing. `acsi-agentskills-private`'s passes no secret, so there it always
only warns. `skills-evals`' `test` is the one required check that fails
closed without it ([the privacy check](skills.md#the-privacy-check)).

`skills-evals` also gets the `eval-scaffold` label, a ruleset on
`roster/proposal` that only the `roster` App and a repo admin can push to,
and a workflow token that can approve pull requests, which is the only
exception to the default above. It and `_agent-guidance` also get a
deletion-only ruleset on `persistent/**`.

**`pull_request_target`.** From 2026-12-02 (moved from 2026-11-02, by
GitHub's
[changelog](https://github.blog/changelog/2026-11-02-pull_request_target-blocked-by-default-december-2)),
GitHub blocks that event on public repos by default unless an Actions
policy allows it. `fleet.yml` allows it
for a single workflow,
`acsi-agentskills`' `.github/workflows/plugin-runtime-review.yml`, which
publishes the required `plugin-runtime-approval` check, and the engine
applies that policy with the other settings. Add any new trigger for that
workflow to the policy first.

`fleet.yml` refers to the two bypass Apps by id, as
`"${GUIDANCE_SYNC_APP_ID}"` and `"${ROSTER_WRITER_APP_ID}"`. Those come from
`repo-settings`' repository variables, and the engine refuses to plan while
either is unset, which is why the Apps come before the first apply.
`"${ROSTER_WRITER_APP_ID}"` appears only in the `skills-evals` element, and
the starter's `fleet.yml` doesn't declare `skills-evals`. That element waits
in `repo-settings/fleet.evals.yml` until the evals track merges it ([the
first apply](#the-first-apply)), so a base-only setup needs only
`guidance-sync`'s id.

After the first apply, `repo-settings.yml` reconciles on every merge and
every Monday at 07:00 UTC. A read-only `plan` job runs with the
`settings-read` App. If it finds drift, the `repo-settings` apply job runs
with the `settings-admin` App, behind the `fleet-apply` environment's
approval. On a pull request, a third job, `drift`, reports what the change
would do. It is advisory, not a required check.

## Environments

`bootstrap/create-environments.sh` creates the three the workflows name:

| Repo | Environment | Protection | Holds |
|---|---|---|---|
| `repo-settings` | `fleet-apply` | you approve; default branch only | `REPO_SETTINGS_APP_PRIVATE_KEY` |
| `acsi-agentskills` | `plugin-runtime-review` | you approve; no branch policy (it runs on `pull_request_target`) | nothing: the approval is the gate |
| `skills-evals` | `routine-fire` | default branch only | `EVAL_ROUTINE_FIRE_BEARER`, `ROUTINE_TRIGGER_ID` |

It also sets `repo-settings`' variables `GUIDANCE_SYNC_APP_ID` and
`ROSTER_WRITER_APP_ID` from `fleet.env` once `create-apps.sh` has filled
them in, so run it again after creating the Apps. From the same file, it
sets `_agent-guidance`'s `FLEET_WORKER_EVERY_HOURS` and `LOOP_WORKER_EVERY_HOURS` (from `CLAUDE_PLAN`),
its `EVALS_REPO` and `ARTICLE_WATCH_FEED_URL` (see [routines](routines.md#fleet-worker)),
`acsi-agentskills`' `EVALS_REPO` (its `ci.yml` reads it too),
and, once `skills-evals` exists, that repo's `SITE_REPO` and four federation
ids. It skips any key left empty in `fleet.env`.

**Updating an existing setup:** each run sets these values to what the plan
and `fleet.env` say, so it replaces a value you set by hand. In particular,
if you set `LOOP_WORKER_EVERY_HOURS` yourself (an earlier kit left it to
you), running `create-environments.sh` again replaces it with your plan's
value (168 on Pro, 24 on Max 5x and Ultra); to keep a different cadence, set
it again afterwards and expect `verify.sh` to report it as differing. The
same run also adds `EVALS_REPO` to `acsi-agentskills`, which its `ci.yml`
now needs, and `bash bootstrap/create-repos.sh` again adds the `ci` label
to repos made before the kit created it.

Until the evals track creates `skills-evals`, the script skips
`routine-fire`, and `ROSTER_WRITER_APP_ID` waits for the `roster` App. The
evals track runs it again (step 37). On `PLAN=free`, the private
`repo-settings` has no environments: `fleet-apply` is skipped,
`create-apps.sh` doesn't create `settings-admin` (its key would have nowhere
to live), the reconcile's apply job never runs, and you apply from your
machine.

**Never approve `plugin-runtime-review` for an agent, and never let one
approve it.** It holds a pull request that changes how a plugin runs code
(hooks, `bin/`, a package install, plugin settings) until you have read it.

## GitHub Apps

The workflows mint short-lived tokens from six Apps, and nothing uses a
personal token. `bootstrap/create-apps.sh` creates each App through GitHub's
App manifest flow. It writes `app-manifests/<app>.html`. You open that file
in a browser signed in as the owner, click Create, and paste back the URL
GitHub redirects to (`http://127.0.0.1/?code=...`). The page won't load, so
copy the URL from the address bar. The one-time code never goes to another
site. The script records the App id in `fleet.env` first, then stores the
client id and private key where the workflows read them, on stdin and never
printed.

GitHub may ask for your password ("Confirm access") when you click Create.
After you confirm, it can drop the manifest and show an empty "Register new
GitHub App" form: don't fill that in. Open `app-manifests/<app>.html` again
and click Create; the script is still waiting for the code. A browser
extension or assistant may hide the `?code=` part of the redirect, so copy
the URL from the address bar yourself.

| App | Permissions | Installed on | Client id | Private key |
|---|---|---|---|---|
| `guidance-sync` | contents, pull requests, issues, workflows: write; actions, checks, metadata: read | every fleet repo | variable `APP_CLIENT_ID` in `_agent-guidance` | secret `APP_PRIVATE_KEY` in `_agent-guidance` |
| `settings-admin` | administration, actions, issues: write; metadata: read | every fleet repo | variable `REPO_SETTINGS_APP_CLIENT_ID` in `repo-settings` | secret `REPO_SETTINGS_APP_PRIVATE_KEY` in `fleet-apply` |
| `settings-read` | administration, actions, issues, metadata: read | every fleet repo | variable `REPO_SETTINGS_READ_APP_CLIENT_ID` in `repo-settings` | secret `REPO_SETTINGS_READ_APP_PRIVATE_KEY` in `repo-settings` |
| `eval-improve` | contents, pull requests: write | `acsi-agentskills`, `_agent-guidance` | secret `EVAL_IMPROVE_APP_CLIENT_ID` in `skills-evals` | secret `EVAL_IMPROVE_APP_PEM` in `skills-evals` |
| `roster` | contents, pull requests: write | `skills-evals` | variable `ROSTER_APP_CLIENT_ID` in `skills-evals` | secret `ROSTER_APP_PRIVATE_KEY` in `skills-evals` |
| `registry-read` | contents: read | `acsi-agentskills-private` | variable `REGISTRY_READ_APP_CLIENT_ID` in `skills-evals` | secret `REGISTRY_READ_APP_PEM` in `skills-evals` |

`guidance-sync` is the owner's `agents-md-sync` App, used by the sync, the
nightly drift report, the skills-lock bumper, and the Dependabot sweep.
`roster`'s id is `ROSTER_WRITER_APP_ID`. `eval-improve`'s client id is a
secret because its gates check that both values exist before minting a
token. App names are `<APP_NAME_PREFIX>-<app>`.

The base needs only the three fleet-wide Apps, created in step 6 (two on
`PLAN=free`, where `create-apps.sh` skips `settings-admin`: see below).
`eval-improve`, `roster`, and `registry-read` serve only evals and keep
their credentials in `skills-evals`. `/adopt-evals` creates and installs
them in steps 33 and 34, once `skills-evals` exists, and `create-apps.sh`
skips them until then.

An older `guidance-sync` made before the kit asked for workflows: write
fails the sync's first delivery to a repo whose workflow files it creates
("refusing to allow a GitHub App to create or update workflow ... without
`workflows` permission"). On the App's settings page, Permissions, set
Repository permissions, Workflows to "Read and write", save, and accept the
new permission on its installation (Settings, Applications, Configure).

A lost private key can't be recovered. Generate a new one on the App's
settings page and store it with the `gh secret set` command `create-apps.sh`
prints for a missing key.

## Installing the Apps

Installing happens in the browser. Open each
`https://github.com/apps/<slug>/installations/new` link `create-apps.sh`
printed, choose "Only select repositories", and pick the repos it names
under the link (the picker closes after each pick, so it takes one round per
repo). If the browser is signed in to two GitHub accounts, the page first
asks which one to install for: pick the owner. For the fleet-wide Apps, that is the five base repos the kit
created, the same list `verify.sh` names for step 7 (not the repos
`fleet.yml` lists, which still include the example repos until step 9). Add
a repo of your own when you list it in `fleet.yml` or `repos.yml`. Once the evals track
creates `skills-evals`, add it to their installations (step 34). With a
second owner, the three are public Apps, so sign in as that owner and
install them there too. `bash bootstrap/verify.sh --only installs:<app>`
checks an installation when it can: GitHub lists installations only to a
GitHub App user token, and answers gh's own sign-in with HTTP 403. Then
verify.sh names each App and the repos it needs; check them at
https://github.com/settings/installations and record your answer with
`bash bootstrap/status.sh --mark 7` (step 34 on the evals track).

## The first apply

`bootstrap/apply-settings.sh` clones your `repo-settings` and checks that
every repo `fleet.yml` declares for the owner exists. It refuses until you
remove the example platform and its sites ([example
repos](generated-files.md#example-repos-in-fleetyml)). It then runs the
engine's `apply` with your `gh` login and reads the result back with the
engine's `diff`, which must report no drift. `--dry-run` shows the engine's
preview, and `--check` does only the read-back
(`verify.sh --only settings`). With a second owner, sign `gh` in as that
account (`gh auth switch`) and run it again with `--owner <OWNER_TWO>`.

`skills-evals` and its `fleet.yml` element belong to the evals track. The
starter ships that element in a fragment, `repo-settings/fleet.evals.yml`,
which nothing applies, so `fleet.yml` alone describes the base. The first
apply needs neither that repo nor the `roster` App's id, and
`repo-settings.yml`'s `plan` job passes with only `GUIDANCE_SYNC_APP_ID`
set. While the fragment exists, `repo-settings`' tests read it along with
`fleet.yml`, so they cover `skills-evals`' settings either way.

`/adopt-evals` creates the repo. Then `bootstrap/regenerate.sh evals-fleet`
(step 40) appends the fragment's element to `fleet.yml`'s `repos:` list,
deletes the fragment, and opens the pull request. Once you merge it, the
same `apply-settings.sh` applies `skills-evals` too and needs
`ROSTER_WRITER_APP_ID` (step 39). `--track base` or `--track evals` limits a
run or a `--check` to one track's repos, and `status.sh` checks each step on
its own track.

From then on, a pull request is the only way to change a default branch. To
confirm, try `git push origin main` from a clone, which GitHub rejects with
`GH013`, and check that squash and rebase are grayed out on a pull request.

## Merging the starter pull requests

`copy-starter.sh` replaces every form of the kit's invented owners with your
names: `example-adopter`, `EXAMPLE_ADOPTER`, `example_adopter`, the second
owner's forms, `Example Adopter`, and `<your name>`. It won't overwrite a
file that differs on your default branch unless you pass `--force`. It opens
a pull request from `starter/<folder>` and never pushes to a default branch.

Review each pull request before merging, because it is a whole repo and its
workflows run on merge. Some checks can't pass yet, either because they read
a generated file that still holds the export's placeholder or because their
workflow isn't on the base branch yet:

- `acsi-agentskills`' `pytest` (its `skills.lock` checks) and every check that
  reads a `skills.lock`: fixed by step 14;
- `acsi-agentskills`' `plugin-runtime-approval`: it runs on
  `pull_request_target`, which uses the base branch's workflow, and an empty
  repo has none, so it never reports on the first pull request;
- anything that verifies `actions.lock` against GitHub, the hook pin or the
  scheduled-run-health pin: steps 15 to 18;
- `skills-evals`' daily `scheduled-run-health.yml` (evals track): it calls
  `_agent-guidance`'s reusable workflow at a sha that ships as forty zeros,
  so the run fails at startup until step 38 pins it. The base repos' copies
  ship with no schedule; step 16 pins the sha and adds the daily schedule in
  the same pull request, so they never run at the placeholder.

Nothing is protected before step 20, so these don't block the merge. Merge
the starter and regenerate pull requests (steps 4 to 18) before step 20, or
their red checks block them once the repos are protected.

The gates that judge a pull request by what it changes against the base
branch pass on a starter pull request: `_agent-guidance`'s "Guidance touch
gate" (in `checks`) and `acsi-agentskills`' skill gates (in `pytest`) find no
guidance or skills on a base that holds only the README, and say there is
nothing to judge. `repo-settings`' `drift` job fails only on drift the pull
request itself brings, not on settings step 20 has yet to apply. Later pull
requests are judged as usual. A repo copied from a kit older than these
fixes (2026-11-27) still shows them red on its starter and `repo-settings`
pull requests; merge them anyway before step 20.

These wait for a later step without failing, each with a "not set up yet"
or "skipped" notice on its run: `repo-settings`' weekly `plan` plans nothing
until `create-apps.sh` sets `REPO_SETTINGS_READ_APP_CLIENT_ID` (step 6; a
merge to `repo-settings` before then still fails at the token mint);
`_agent-guidance`'s `fleet-worker-fire.yml` fires no Fleet worker while
`FLEET_WORKER_FIRE_URL` is `none`, the value `create-environments.sh` writes
until step 27 sets the routine's URL (`verify.sh --only fleet-worker`, step
27's check, reports it until then), and the same for the Loop worker's
`LOOP_WORKER_FIRE_URL` until step 41; and the
scheduled runs that read `skills-evals` skip while `EVALS_REPO` is `none`
([routines](routines.md#fleet-worker)); and `_agent-guidance`'s `sync.yml`
skips each repo whose README still carries the last line `create-repos.sh`
wrote ("Not set up yet") until steps 12 and 13 merge its starter, so nothing
lands there before `copy-starter.sh` does. For a repo you set up by hand,
delete that line.

`_agent-guidance`'s vendor notes (`docs/reference/agent-*.DISCREPANCIES.md`
and `docs/reference/vendor-issue-drafts/`) ship with no entries, so merging
its starter opens no "Vendor discrepancy" issue. A copy from an older kit
shipped the source owner's notes, and `vendor-discrepancy-alert.yml` opened
one issue per entry: those are the owner's findings, not yours, so close
them.

One issue is expected on the evals track, and no run fails for it. Between
step 35, which creates `skills-evals`, and step 40, which lists it in
`repos.yml`'s `cron_coverage.fleet`, `_agent-guidance`'s daily
`drift-report.yml` opens "Unclassified for cron coverage" naming
`skills-evals`. The first report after step 40's pull request is merged
closes it.

These are expected to fail until a later step or a kit update, and nothing
else is:

- merging `repo-settings`' starter pull request (step 4) runs its `plan`,
  which fails at the token mint until step 6 creates the settings-read App,
  and then at the label read until step 9 drops the example repos from
  `fleet.yml` (a re-run after step 9 is green);
- `_agent-guidance`'s `sync.yml` with a `guidance-sync` App made before the
  kit asked for workflows: write: its first delivery of workflow files to a
  repo fails (see [GitHub Apps](#github-apps)). An `_agent-guidance` copied
  from a kit older than 2026-11-27 also syncs repos that hold only their
  README, from step 10 until steps 12 and 13: the run reports the files the
  sync expects there and doesn't find. If it delivers files there first and
  `copy-starter.sh` then refuses one, check the two differ only in what the
  starter adds and run it again with `--force`;
- `_agent-guidance`'s `skills-lock-bump.yml`, four times a day from step 10
  until step 12 copies `acsi-agentskills` (until then that repo holds only
  its first README). A later kit update fixes this one;
- `_agent-guidance`'s daily `dependabot-config-health.yml`, from step 10
  until step 11 removes the three `example-site-*` names from `repos.yml`'s
  `cron_coverage.fleet`: it fails on a name neither owner has. The list
  doesn't name `skills-evals` until step 40 adds it, so a setup without
  `skills-evals` is green from step 11 on.

Any other failure is real: read it before you merge.

On `PLAN=free`, `create-apps.sh` skips the `settings-admin` App, so
`REPO_SETTINGS_APP_CLIENT_ID` is never set in `repo-settings`. Both apply
jobs in `repo-settings.yml` (`apply-auto` and `repo-settings`) check that
variable and are skipped. The weekly `plan` job doesn't need it: it runs with
the read App and reports drift. You apply from your machine with
`bash bootstrap/apply-settings.sh`.

On `PLAN=paid`, until step 20, `repo-settings.yml`'s apply job waits for
your approval on each merge to `repo-settings`. Reject those deployments
until then. On `PLAN=free` nothing waits for you: `repo-settings` has no
`fleet-apply` environment. A merge that changes one of the files
`repo-settings.yml` watches on a push (`repo-settings/fleet.yml`,
`scripts/repo_settings.py`, the workflow itself, `requirements.txt`) starts
a run that shows both apply jobs as skipped and the `plan` job's drift
report, with nothing to approve or reject; any other merge starts no run.
Step 20 applies from your machine.
