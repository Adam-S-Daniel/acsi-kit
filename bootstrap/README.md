# Bootstrap scripts

These scripts do the part of adopting the system that can be scripted, on
your own account, with the GitHub CLI (`gh`). The order is
[`steps.json`](steps.json), rendered in
[the quick start](../docs/quick-start.md); `status.sh` says where you are
and the [`/adopt` skill](../.claude/skills/adopt/SKILL.md) walks you
through it (and [`/adopt-evals`](../.claude/skills/adopt-evals/SKILL.md)
through the eval steps).

Every script:

- reads one config file, `fleet.env` (`--config <path>`, default
  `./fleet.env`), parsed, never sourced;
- has `--dry-run`, which makes the same reads and prints each write call
  instead of making it;
- is idempotent: it reads first and writes only what differs, so a second
  run prints `Nothing to change`;
- prints an HTTP status or a fixed message on error, never a response body;
- has a usage header (`<script> --help`).

You need bash 4.4 or newer, `gh` (signed in as the owner, with the
`workflow` scope so pushes can add workflow files:
`gh auth refresh -s workflow`), `jq`, `git` and `python3` with PyYAML.
`regenerate.sh actions-lock` also needs the `gh actions-lock` extension, and
Claude Code installs the plugins `install-machine.sh` enables in its next
session.

## The scripts

| Script | Does | Cannot |
|---|---|---|
| `fleet.env.example` | The one file you fill in: owners, plan, visibility, `REPOS_DIR`, and the App ids `create-apps.sh` records. No secrets, ever. | |
| `add-content.sh` | Adds the recommended and opinionated items you name (`--items <ids\|recommended\|none>`, from `content-catalog.json`) to the kit copy's `../starter/` from `../library/`, rebuilds the generated files they feed (through `lib/content.py`), and records your choices beside `status.sh`'s state file. Idempotent; `--dry-run` lists the files it would add or change. | Write to GitHub: once the repos exist it lists the repos that need a pull request. Run inside a git work tree. |
| `create-repos.sh` | The five base repos, and `skills-evals` only when named (the evals track's first step) or once it exists (`FLEET_REPOS` and `EVALS_REPO` in `lib/common.sh`), with the owner's visibility, a generated README as the first commit, the labels `agent-ready` and `on-hold`, and, in `skills-evals`, the orphan branch `persistent/eval-results` (a README only) that the eval loop's workflows fetch and nothing else creates. `--with-optional` adds the private `waiting-feed`. | Change an existing repo's visibility (it reports the mismatch and exits 1). Every other setting is `fleet.yml`'s, applied by `apply-settings.sh`. |
| `copy-starter.sh` | Clones one of your repos, copies an export from `../starter/` into it with your names (every form of the invented owners, and `<your name>`, through `lib/substitute.py`), commits on `starter/<folder>`, pushes, checks the commit is on the remote branch, and opens a pull request. Refuses to overwrite a file that differs unless `--force`, except the README `create-repos.sh` generated. | Merge it: review it yourself, above all `.github/workflows/`. |
| `create-environments.sh` | The three environments (`ENVIRONMENTS`): `fleet-apply` in `repo-settings` and `routine-fire` in `skills-evals`, limited to the default branch, and `plugin-runtime-review` in `acsi-agentskills` with you as reviewer. Then the repository variables in `REPO_VARIABLES` (`repo-settings`' `GUIDANCE_SYNC_APP_ID` and `ROSTER_WRITER_APP_ID`, `skills-evals`' required `SITE_REPO` (`none`: no website), and, when you fill them in, `skills-evals`' four optional `ANTHROPIC_*` federation ids, all from `fleet.env`). While `skills-evals` does not exist, what lives in it is skipped. | Create an environment in a private repo on GitHub Free (it says so and skips it). Delete an extra branch policy (it reports it). |
| `create-apps.sh` | The six Apps (`APPS`) through GitHub's App manifest flow: writes `app-manifests/<app>.html`, exchanges the code from the URL you paste, records the App id in `fleet.env`, stores the client id and private key under the names the workflows read, on stdin, and prints the install link and the repos to pick. The three evals Apps keep their credentials in `skills-evals`, so they wait for it. | Click Create or install an App for you. Recover a lost key. |
| `set-secrets.sh` | `PRIVACY_DENYLIST` in `acsi-agentskills` (`--only privacy`: the file must be outside every git work tree and every line must compile), and `EVAL_ROUTINE_FIRE_BEARER` and `ROUTINE_TRIGGER_ID` in `skills-evals`' `routine-fire` environment (`--only routine-fire`), from a hidden prompt or the file, on stdin. `--rotate` replaces values already set. | Read the bearer from claude.ai: you copy it from the routine's API trigger. Compare a stored secret (GitHub never shows one). |
| `regenerate.sh <task>` | Rebuilds a generated file the export could not (`skills-locks`, `hook-pin`, `run-health-sha`, `codex-pin`, `actions-lock`) with the repo's own tooling, on a clone, and proposes it as a pull request on `regenerate/<task>`. `evals-fleet` (the evals track's) merges `repo-settings`' `repo-settings/fleet.evals.yml`, the `skills-evals` element, into `repo-settings/fleet.yml` with `lib/fleet_fragment.py` and deletes the fragment. `--check` reads the default branches and exits 1 while it is not done. `skills-evals` counts once it exists; `--track base\|evals` limits a task to one track's repos. | Merge what it opens. |
| `apply-settings.sh` | Clones your `repo-settings` and runs its own engine, `scripts/repo_settings.py`, on `repo-settings/fleet.yml` for one owner: `apply`, then `diff`, which must report no drift. The starter's `fleet.yml` declares no `skills-evals` until `regenerate.sh evals-fleet`'s pull request adds it. Refuses while `fleet.yml` names a repo that does not exist; `--track base\|evals` limits it to one track's repos (a copy of `fleet.yml` without, or with only, `skills-evals`). `--dry-run` is the engine's preview, `--check` the `diff` alone. | Apply for the second owner while `gh` is signed in as the first (sign in as that account and pass `--owner`). |
| `install-machine.sh` | On one durable machine: clones or fast-forwards `acsi-agentskills` and `_agent-guidance` into `REPOS_DIR` and runs their installers: `setup.sh --owner-machine`, `scripts/install-agent-hooks.sh`, `scripts/register-memory-home-hook.sh`, and with `--with-codex` `scripts/register-codex-hook.sh`. | Install git 2.54+, PyYAML or Codex. Trust the Codex hook (`/hooks` in Codex). |
| `verify.sh` | Read-only PASS, FAIL or SKIP per group: `repos`, `labels`, `branches`, `environments`, `variables`, `apps:<app>`, `installs:<app>`, `values:<group>`; `settings` (the engine's `diff`) and `regen:<task>` only when named with `--only`; `content` (each installed optional item is on its repo's default branch) once `add-content.sh` has recorded your choices. `--track base\|evals` scopes every group to one track (`status.sh` passes each step's); the default checks both, or only the base while `skills-evals` does not exist. Names of variables and secrets only, never a value. | See a secret's value, or anything outside GitHub (routines, cloud environments, machines). |
| `status.sh` | Read-only: one line per step (done, next, todo, optional, asked: done), how many steps of each track (base, evals) are done, then the next step with its time, kind, what to run and the section to read. `--track base\|evals` limits it to one track. `--mark`/`--unmark` record the steps nothing can see, in a state file outside every repo. | Decide an ask step for you. |
| `render-quickstart.py` | Writes the steps table, with each step's track, into `../docs/quick-start.md`; `--check` fails when it is stale. | |

The libraries: `lib/common.sh` (config parsing, the registries of repos,
environments, Apps, values and variables, and the `gh` wrappers that honor
`--dry-run`), `lib/pr.sh` (branch, commit, push, verify and open a pull
request; never a default branch, never a force push),
`lib/substitute.py` (the owner names) and `lib/content.py` (the library
installer `add-content.sh` runs).

## Variables and secrets set by hand

Every `vars.NAME` and `secrets.NAME` an exported workflow reads is set by a
script: App client ids and keys by `create-apps.sh`, `PRIVACY_DENYLIST`,
`EVAL_ROUTINE_FIRE_BEARER` and `ROUTINE_TRIGGER_ID` by `set-secrets.sh`,
and the repository variables by `create-environments.sh` (`SITE_REPO`
included, from `fleet.env`), except the site ones below. If you add a workflow that reads a value no script
sets, list it here as a list item, "- `NAME`: where it lives and how to set
it"; `tests/check-refs.py` fails on any name that is neither set by a script
nor listed here, and on a name listed here that a script already sets or
nothing reads.

The site ones are for publishing the Evals Explorer to a website of your own
(`skills-evals`' `site-sync.yml` and `site-freshness.yml`,
[routines](../docs/routines.md#dashboard-refresh)). Neither workflow has a
default for any of them. Which site, if any, is `SITE_REPO` in `fleet.env`,
and it is required: `none` (what `fleet.env.example` ships) means no
website, and both workflows skip; `owner/name` names your site repo; left
empty, `create-environments.sh` skips it and says so, and the workflows then
fail naming it. The four below are needed only with a site; with
`SITE_REPO=none`, leave them unset.

- `SITE_PAGE_URL`: a repository variable on `<you>/skills-evals`, the live
  page's URL that `site-freshness.yml` loads. Set it with
  `gh variable set SITE_PAGE_URL --repo <you>/skills-evals --body <url>`.
- `SITE_ASSET_URL`: a repository variable on `<you>/skills-evals`, the URL of
  the vendored page file on the site. Set it the same way.
- `SITE_FRESHNESS_ROUTINE_ID`: a repository variable on `<you>/skills-evals`,
  the `trig_...` id of a routine made from `skills-evals`'
  `docs/routines/site-freshness-fixer.md`, which `site-freshness.yml` fires
  when the site stays stale. Set it the same way.
- `SITE_FRESHNESS_FIRE_BEARER`: a repository secret on `<you>/skills-evals`,
  that routine's bearer, shown once when you create it. Set it with
  `gh secret set SITE_FRESHNESS_FIRE_BEARER --repo <you>/skills-evals` and
  type the value at its prompt.

The prompt-audit sweep's fire values live on `_agent-guidance`, where
`prompt-audit-fire.yml` fires the sweep for each trigger issue the changelog
watcher files ([routines](../docs/routines.md#prompt-audit-sweep)). Unset,
the workflow comments on the issue that the fire is not configured, and you
start the sweep by hand.

- `PROMPT_AUDIT_SWEEP_FIRE_URL`: a repository variable on
  `<you>/_agent-guidance`, the sweep routine's fire URL
  (`https://api.anthropic.com/v1/claude_code/routines/<trig_id>/fire`). Set
  it with `gh variable set PROMPT_AUDIT_SWEEP_FIRE_URL --repo <you>/_agent-guidance --body <url>`.
- `PROMPT_AUDIT_SWEEP_FIRE_BEARER`: a repository secret on
  `<you>/_agent-guidance`, the sweep routine's bearer, shown once when you
  create its API trigger. Set it with
  `gh secret set PROMPT_AUDIT_SWEEP_FIRE_BEARER --repo <you>/_agent-guidance`
  and type the value at its prompt.

## Security

- No value from `fleet.env` or GitHub reaches a shell command unquoted; each
  key is validated when it is parsed.
- JSON bodies are built with `jq` or Python and passed on stdin.
- A private key, client secret, bearer or denylist goes to `gh` on stdin
  from `printf` (a builtin, so never in a process list) or from the file
  itself, and is never printed, logged or written to disk. The manifest
  conversion response is dropped as soon as its fields are read.
- No script pushes to a default branch or force-pushes; each checks its
  commit is on the remote branch after the push
  (`git merge-base --is-ancestor`).
- `apply-settings.sh` runs the engine from a fresh clone of your own
  `repo-settings`, with `python3 -I`.

## Tests

```bash
bash tests/test-bootstrap.sh
```

No network, no sleeps, no wall clock. `tests/stubs/gh` is a stateful `gh`
stand-in that logs every argv (it stores secrets only as SHA-256). The git
remotes are local bare repos (`BOOTSTRAP_GIT_BASE`), with a scratch `HOME`
and `GIT_CONFIG_GLOBAL`: the real `copy-starter.sh` copies all six exports
in, the test merges them, and the real `regenerate.sh` runs each repo's own
generator on them. `apply-settings.sh` and `install-machine.sh` run against
repos holding a fake engine and fake installers that log their arguments;
the real engine's `--help` is checked for every flag the script passes. Run
it in a PID namespace (`unshare --pid --fork --mount-proc --`, or with
`--user --map-current-user` when not root). The suite also runs the
checkers: `tests/check-refs.py` holds every workflow's variables and secrets
to the scripts that set them; `tests/check-branch-prefixes.py` holds the
routine prompt, the gates and the docs to one set of loop branch lanes;
`tests/check-guide-lists.py` holds the docs to the workflows, Apps,
environments and `REGENERATE.md`; `tests/check-steps.py` checks
`steps.json`; `tests/check-links.py` resolves every relative link and anchor
in the kit's own pages.
