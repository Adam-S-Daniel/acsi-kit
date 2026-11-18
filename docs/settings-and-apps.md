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
later replaces. The script also creates the two labels no settings file
declares: `agent-ready` (the fleet worker's queue) and `on-hold` (paused by
you, and only you add or remove it).

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
| `acsi-agentskills` | `privacy`, `pytest`, `pytest-windows`, `plugin-runtime-approval`, `agent-checks`, `merge-gate` |
| `skills-evals` | `test`, `agent-checks` |
| `_agent-guidance` | `test`, `agent-checks` |
| `wsl-automation` | `shell`, `test`, `test-linux`, `agent-checks` |
| `repo-settings` | `agent-checks`, `unit` |
| `acsi-agentskills-private` | `agent-checks` |

`privacy` fails closed without the `PRIVACY_DENYLIST` secret, so store it
before the `acsi-agentskills` starter pull request
([the privacy check](skills.md#the-privacy-check)).

`skills-evals` also gets the `eval-scaffold` label, a ruleset on
`roster/proposal` that only the `roster` App and a repo admin can push to,
and a workflow token that can approve pull requests, which is the only
exception to the default above. It and `_agent-guidance` also get a
deletion-only ruleset on `persistent/**`.

**`pull_request_target`.** From 2026-11-02, GitHub blocks that event on public
repos by default unless an Actions policy allows it. `fleet.yml` allows it
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
sets `_agent-guidance`'s `FLEET_WORKER_EVERY_HOURS` (from `CLAUDE_PLAN`)
and, once `skills-evals` exists, that repo's `SITE_REPO` and four federation
ids. It skips any key left empty in `fleet.env`.

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

| App | Permissions | Installed on | Client id | Private key |
|---|---|---|---|---|
| `guidance-sync` | contents, pull requests, issues: write; actions, checks, metadata: read | every fleet repo | variable `APP_CLIENT_ID` in `_agent-guidance` | secret `APP_PRIVATE_KEY` in `_agent-guidance` |
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

The base needs only the three fleet-wide Apps, created in step 6.
`eval-improve`, `roster`, and `registry-read` serve only evals and keep
their credentials in `skills-evals`. `/adopt-evals` creates and installs
them in steps 33 and 34, once `skills-evals` exists, and `create-apps.sh`
skips them until then.

A lost private key can't be recovered. Generate a new one on the App's
settings page and store it with the `gh secret set` command `create-apps.sh`
prints for a missing key.

## Installing the Apps

Installing happens in the browser. Open each
`https://github.com/apps/<slug>/installations/new` link `create-apps.sh`
printed, choose "Only select repositories", and pick the repos listed in the
table. For the three fleet-wide Apps, that means the kit repos you created
and every consumer in `_agent-guidance`'s `repos.yml`. Once the evals track
creates `skills-evals`, add it to their installations (step 34). With a
second owner, the three are public Apps, so sign in as that owner and
install them there too. `bash bootstrap/verify.sh --only installs:<app>`
checks an installation.

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
  scheduled-run-health pin: steps 15 to 18.

Nothing is protected before step 20, so these don't block the merge. Any
other failure is real, so read it before you merge.

Until step 20, `repo-settings.yml`'s apply job waits for your approval on
each merge to `repo-settings`. Reject those deployments until then.
