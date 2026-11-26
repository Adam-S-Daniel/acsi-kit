# Bootstrap scripts

These scripts automate what can be automated when you adopt the system on
your own account, using the GitHub CLI (`gh`). [`steps.json`](steps.json)
sets the order, and [the quick start](../docs/quick-start.md) shows it.
`status.sh` says where you are, the [`/adopt`
skill](../.claude/skills/adopt/SKILL.md) walks you through the base, and
[`/adopt-evals`](../.claude/skills/adopt-evals/SKILL.md) walks you through
the eval steps.

Every script:

- reads one config file, `fleet.env` (`--config <path>`, default
  `./fleet.env`), which it parses and never sources;
- has `--dry-run`, which makes the same reads and prints each write call
  instead of making it;
- is idempotent: it reads first and writes only what differs, so a second
  run prints `Nothing to change`;
- prints an HTTP status or a fixed message on error, never a response body;
- has a usage header (`<script> --help`).

You need bash 4.4 or newer, `jq`, `git`, `python3` with PyYAML, and `gh`,
signed in as the owner with the `workflow` scope so pushes can add workflow
files (`gh auth refresh -s workflow`). `regenerate.sh actions-lock` also
needs the `gh actions-lock` extension. Claude Code installs the plugins
`install-machine.sh` enables in its next session.

## The scripts

| Script | Does | Cannot |
|---|---|---|
| `fleet.env.example` | The only file you fill in: owners, plan, `TIME_ZONE`, visibility, `REPOS_DIR`, and the App ids `create-apps.sh` records. No secrets, ever. | |
| `add-content.sh` | Adds the recommended and opinionated items you name (`--items <ids\|recommended\|none>`, from `content-catalog.json`) to the kit copy's `../starter/` from `../library/`, rebuilds the generated files they feed (through `lib/content.py`), and records your choices beside `status.sh`'s state file. Idempotent; `--dry-run` lists the files it would add or change. | Write to GitHub: once the repos exist it lists the repos that need a pull request. Run inside a git work tree. |
| `update-kit.sh` | Moves a clone of the kit to the newest kit; the README's update block runs the newest copy of it from a temporary folder (`--kit <clone>`), so it also updates a clone older than the script (`--dry-run` reports only). It checks your `fleet.env` with the newer kit's loader, proves that your `starter/` changes are exactly what `add-content.sh` wrote (contents and executable bits), saves every `starter/` change to `~/kit-starter-backup-<commit>`, discards them, fast-forwards to `origin/HEAD`, lists the `fleet.env` keys `fleet.env.example` added (required or optional) or removed since your old commit (names only), and runs `add-content.sh` again with your recorded choices, dropping any the catalog no longer offers. A detached HEAD, a merge or rebase in progress, a tracked edit outside `starter/`, a hand edit in `starter/` (unless `--discard-starter-edits`), no `fleet.env` at `--config` while `starter/` has changes or a choices record exists, a `fleet.env` the newer kit refuses or a local commit makes it refuse before it changes anything. Exits 0 only when it all worked; an interrupt or failure says where things stand and what to run next. | Change repos you already filled from an older starter (use `copy-starter.sh --dry-run`), update a downloaded copy that is not a git clone, or write to GitHub. |
| `create-repos.sh` | The five base repos, and `skills-evals` only when named (the evals track's first step) or once it exists (`FLEET_REPOS` and `EVALS_REPO` in `lib/common.sh`), with the owner's visibility, a generated README as the first commit, the labels `agent-ready`, `on-hold` and `ci` (the scheduled workflows file their issues under `ci`, and `gh issue create --label` fails on a label the repo lacks), and, in `skills-evals`, the orphan branch `persistent/eval-results` (a README only) that the eval loop's workflows fetch and nothing else creates. `--with-optional` adds the private `waiting-feed`. | Change an existing repo's visibility (it reports the mismatch and exits 1). Every other setting is `fleet.yml`'s, applied by `apply-settings.sh`. |
| `copy-starter.sh` | Clones one of your repos, copies an export from `../starter/` into it with your names (every form of the invented owners, and `<your name>`, through `lib/substitute.py`, and your `TIME_ZONE` into `_agent-guidance`'s `scripts/base-md-merge-window.yml`, through `lib/time_zone.py`, which refuses a tree without that one `timezone: UTC` line), commits on `starter/<folder>`, pushes, checks the commit is on the remote branch, and opens a pull request. Refuses to overwrite a file that differs unless `--force`, except the README `create-repos.sh` generated. | Merge it: review it yourself, above all `.github/workflows/`. |
| `create-environments.sh` | The three environments (`ENVIRONMENTS`): `fleet-apply` in `repo-settings` and `routine-fire` in `skills-evals`, limited to the default branch, and `plugin-runtime-review` in `acsi-agentskills` with you as reviewer. Then the repository variables in `REPO_VARIABLES` (`repo-settings`' `GUIDANCE_SYNC_APP_ID` and `ROSTER_WRITER_APP_ID`, `skills-evals`' required `SITE_REPO` (`none`: no website), and, when you fill them in, `skills-evals`' four optional `ANTHROPIC_*` federation ids, all from `fleet.env`), plus on `_agent-guidance` the `FLEET_WORKER_EVERY_HOURS` and `LOOP_WORKER_EVERY_HOURS` cadences (from `CLAUDE_PLAN`), `EVALS_REPO` (`none` while `skills-evals` does not exist, `<you>/skills-evals` once it does, so the evals track's run flips it) and `ARTICLE_WATCH_FEED_URL` (`none`, which turns the optional article watch off, only while it is not set at all: a feed URL you set is never overwritten), and `FLEET_WORKER_FIRE_URL` and `LOOP_WORKER_FIRE_URL` (`none`, "not set up yet", by the same rule, until steps 27 and 41 set the routines' URLs); `acsi-agentskills` gets `EVALS_REPO` too. While `skills-evals` does not exist, what lives in it is skipped. | Create an environment in a private repo on GitHub Free (it says so and skips it). Delete an extra branch policy (it reports it). |
| `create-apps.sh` | The six Apps (`APPS`) through GitHub's App manifest flow: writes `app-manifests/<app>.html`, exchanges the code from the URL you paste, records the App id in `fleet.env`, stores the client id and private key under the names the workflows read, on stdin, and prints the install link and the repos to pick. The three evals Apps keep their credentials in `skills-evals`, so they wait for it. | Click Create or install an App for you. Recover a lost key. |
| `set-secrets.sh` | `PRIVACY_DENYLIST` in `acsi-agentskills` (`--only privacy`: the file must be outside every git work tree and every line must compile), and `EVAL_ROUTINE_FIRE_BEARER` and `ROUTINE_TRIGGER_ID` in `skills-evals`' `routine-fire` environment (`--only routine-fire`), from a hidden prompt or the file, on stdin. `--rotate` replaces values already set. | Read the bearer from claude.ai: you copy it from the routine's API trigger. Compare a stored secret (GitHub never shows one). |
| `regenerate.sh <task>` | Rebuilds a generated file the export could not (`skills-locks`, `hook-pin`, `run-health-sha`, `codex-pin`, `actions-lock`) with the repo's own tooling, on a clone, and proposes it as a pull request on `regenerate/<task>`. `run-health-sha` also sets your `_agent-guidance` commit in the two other places `acsi-agentskills` names one (`scripts/cloud-env-setup.sh`, which cloud sessions install the guidance with, and the eval-protection gate's checkout in `ci.yml`), and, before it writes the first of those, refuses when the two repos' copies of the guidance installer differ; `codex-pin` sets both pins of the Codex Cloud sync script. `evals-fleet` (the evals track's) merges `repo-settings`' `repo-settings/fleet.evals.yml`, the `skills-evals` element, into `repo-settings/fleet.yml` with `lib/fleet_fragment.py` and deletes the fragment. `--check` reads the default branches and exits 1 while it is not done. `skills-evals` counts once it exists; `--track base\|evals` limits a task to one track's repos. | Merge what it opens. |
| `apply-settings.sh` | Clones your `repo-settings` and runs its own engine, `scripts/repo_settings.py`, on `repo-settings/fleet.yml` for one owner: `apply`, then `diff`, which must report no drift. The starter's `fleet.yml` declares no `skills-evals` until `regenerate.sh evals-fleet`'s pull request adds it. Refuses while `fleet.yml` names a repo that does not exist; `--track base\|evals` limits it to one track's repos (a copy of `fleet.yml` without, or with only, `skills-evals`). `--dry-run` is the engine's preview, `--check` the `diff` alone. | Apply for the second owner while `gh` is signed in as the first (sign in as that account and pass `--owner`). |
| `install-machine.sh` | On one durable machine: clones or fast-forwards `acsi-agentskills` and `_agent-guidance` into `REPOS_DIR` and runs their installers: `setup.sh --owner-machine`, `scripts/install-agent-hooks.sh`, `scripts/register-memory-home-hook.sh`, and with `--with-codex` `scripts/register-codex-hook.sh`. | Install git 2.54+, PyYAML or Codex. Trust the Codex hook (`/hooks` in Codex). |
| `verify.sh` | Read-only PASS, FAIL or SKIP per group: `repos`, `labels`, `branches`, `environments`, `variables`, `apps:<app>`, `installs:<app>`, `values:<group>`; `settings` (the engine's `diff`) and `regen:<task>` only when named with `--only`; `content` (each installed optional item is on its repo's default branch) once `add-content.sh` has recorded your choices. `--track base\|evals` scopes every group to one track (`status.sh` passes each step's); the default checks both, or only the base while `skills-evals` does not exist. Names of variables and secrets only, never a value. | See a secret's value, or anything outside GitHub (routines, cloud environments, machines). |
| `preflight.sh` | Read-only, on this machine only: PASS, FAIL, WARN or SKIP per tool the scripts need (`git`, `gh`, `jq`, `python3` with PyYAML, `node`, `npm`, bash 4.4+ through `lib/common.sh`), whether `gh` is signed in as `OWNER` with the `workflow` and `repo` scopes, and where the kit sits. Every FAIL and WARN carries the install command for your OS (`brew`, `apt-get`, `dnf`). `--track` is accepted like its neighbors' but changes nothing, since no check serves one track only. | Install anything, or write to GitHub or to disk. |
| `status.sh` | Read-only: one line per step (done, next, todo, optional, asked: done), how many steps of each track (base, evals) are done, then the next step with its time, kind, what to run and the section to read. `--track base\|evals` limits it to one track. `--mark`/`--unmark` record the steps nothing can see, in a state file outside every repo. | Decide an ask step for you. |
| `render-quickstart.py` | Writes the steps table, with each step's track, into `../docs/quick-start.md`; `--check` fails when it is stale. | |

The libraries are `lib/common.sh` (config parsing, the registries of repos,
environments, Apps, values, and variables, and the `gh` wrappers that honor
`--dry-run`), `lib/pr.sh` (branch, commit, push, verify, and open a pull
request, never on a default branch and never with a force push),
`lib/substitute.py` (the owner names), and `lib/content.py` (the library
installer `add-content.sh` runs).

## Variables and secrets set by hand

A script sets every `vars.NAME` and `secrets.NAME` an exported workflow
reads, except the ones listed below. `create-apps.sh` sets App client ids
and keys. `set-secrets.sh` sets `PRIVACY_DENYLIST`,
`EVAL_ROUTINE_FIRE_BEARER`, and `ROUTINE_TRIGGER_ID`.
`create-environments.sh` sets the repository variables, including
`SITE_REPO` from `fleet.env`, `EVALS_REPO` (`none` or `<you>/skills-evals`,
which `fleet-worker-fire.yml` and `impact-report.yml` read and have no default
for) and `ARTICLE_WATCH_FEED_URL` (`none` until you set a feed URL).

If you add a workflow that reads a value no script sets, add it here as a
list item: "- `NAME`: where it lives and how to set it".
`tests/check-refs.py` fails on any name that is neither set by a script nor
listed here, and on a listed name that a script already sets or nothing
reads.

These first values publish the Evals Explorer to your own website
(`skills-evals`' `site-sync.yml` and `site-freshness.yml`,
[routines](../docs/routines.md#dashboard-refresh)). Neither workflow has a
default for any of them. `SITE_REPO` in `fleet.env` is required and says
which site to use, if any. `none`, which `fleet.env.example` ships, means no
website, and both workflows skip. `owner/name` names your site repo. If it
is empty, `create-environments.sh` skips it and says so, and the workflows
then fail and name it. The values below matter only with a site, so leave
them unset with `SITE_REPO=none`.

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
- `SITE_PREVIEW_URL`: a repository variable on `<you>/skills-evals`, the
  preview page's URL with `{pr}` where the site pull request's number goes,
  which `site-preview.yml` comments on a pull request. Set it the same way as
  `SITE_PAGE_URL`.

The privacy comment alert (`privacy-comment-alert.yml`, which the sync
delivers with agent-checks) sends its alert through a self-alert route that
the kit does not include: a GitHub App that can dispatch a self-alert
workflow you write, named send-self-alert.yml, in a repository of your own. Without
these three values it scans nothing it can report and only warns, so leave
them unset unless you build that route.

- `SELF_ALERT_APP_ID`: a repository variable on each repo that runs the
  alert, the route App's client id. Set it with
  `gh variable set SELF_ALERT_APP_ID --repo <you>/<repo> --body <id>`.
- `SELF_ALERT_REPO`: a repository variable on the same repos, the
  `owner/name` of the repository that holds that workflow. Set it the
  same way.
- `SELF_ALERT_APP_PRIVATE_KEY`: a repository secret on the same repos, the
  route App's private key. Set it with
  `gh secret set SELF_ALERT_APP_PRIVATE_KEY --repo <you>/<repo> < <key file>`.

The prompt-audit sweep's fire values live on `_agent-guidance`, where
`prompt-audit-fire.yml` fires the sweep for each trigger issue the changelog
watcher files ([routines](../docs/routines.md#prompt-audit-sweep)). If they
are unset, the workflow comments on the issue that the fire isn't
configured, and you start the sweep by hand.

- `PROMPT_AUDIT_SWEEP_FIRE_URL`: a repository variable on
  `<you>/_agent-guidance`, the sweep routine's fire URL
  (`https://api.anthropic.com/v1/claude_code/routines/<trig_id>/fire`). Set
  it with `gh variable set PROMPT_AUDIT_SWEEP_FIRE_URL --repo <you>/_agent-guidance --body <url>`.
- `PROMPT_AUDIT_SWEEP_FIRE_BEARER`: a repository secret on
  `<you>/_agent-guidance`, the sweep routine's bearer, shown once when you
  create its API trigger. Set it with
  `gh secret set PROMPT_AUDIT_SWEEP_FIRE_BEARER --repo <you>/_agent-guidance`
  and type the value at its prompt.

`_agent-guidance`'s `fleet-worker-fire.yml` fires the fleet worker on the
cadence in `FLEET_WORKER_EVERY_HOURS`, which `create-environments.sh` sets
from `CLAUDE_PLAN`: weekly (168) on Pro, every 12 hours on Max 5x, every 3
hours on Ultra ([routines](../docs/routines.md#fleet-worker)). The workflow
has no default for either value below. `create-environments.sh` sets
`FLEET_WORKER_FIRE_URL` to `none` while it is not set at all, and each
scheduled run then skips the fire with a "not set up yet" notice (a setup
before step 27). Step 27 replaces `none` with the routine's URL; from then
on an empty URL (a deleted variable), a missing bearer or a failed fire fails
the run. `verify.sh --only fleet-worker` (step 27's check) reports a URL
that is unset or still `none`, and a missing bearer.

- `FLEET_WORKER_FIRE_URL`: a repository variable on `<you>/_agent-guidance`,
  the fleet worker routine's fire URL. Set it like
  `PROMPT_AUDIT_SWEEP_FIRE_URL`.
- `FLEET_WORKER_FIRE_BEARER`: a repository secret on `<you>/_agent-guidance`,
  that routine's bearer. Set it like `PROMPT_AUDIT_SWEEP_FIRE_BEARER`.

The same workflow fires a second task, the Loop worker
([routines](../docs/routines.md#fleet-worker)), with its own values. It serves
the eval loop, so it belongs to the evals track: while `EVALS_REPO` is `none`
(a base-only setup), its fire is skipped with a notice and needs none of these.
`create-environments.sh` sets `LOOP_WORKER_FIRE_URL` to `none` while it is not
set at all, which also skips the fire with a notice. Once `skills-evals` exists, set them (replacing `none`) before `create-environments.sh` runs again
(the evals track's step 41, before step 37): that run flips `EVALS_REPO` to
`skills-evals`, and a scheduled fire then fails while either is unset. Its cadence, `LOOP_WORKER_EVERY_HOURS`,
is not among them: `create-environments.sh` sets it from `CLAUDE_PLAN`, like
the fleet worker's (168 on Pro, else 24), on every track.

- `LOOP_WORKER_FIRE_URL`: a repository variable on `<you>/_agent-guidance`,
  the Loop worker routine's fire URL. Set it like `PROMPT_AUDIT_SWEEP_FIRE_URL`.
- `LOOP_WORKER_FIRE_BEARER`: a repository secret on `<you>/_agent-guidance`,
  that routine's bearer. Set it like `PROMPT_AUDIT_SWEEP_FIRE_BEARER`.

`repo-settings`' `repo-settings.yml` can also apply tightening changes with no
approval, through an optional second environment, `fleet-apply-auto`. The kit
does not create it: `fleet-apply` is the one `create-environments.sh` makes. To
turn it on, create `fleet-apply-auto` on `<you>/repo-settings` with no required
reviewer, limit its deployment branches to `main`, and add the same
`REPO_SETTINGS_APP_PRIVATE_KEY` to it as an environment secret. Until all three
are true the `apply-auto` job applies nothing and every change waits for the
reviewed apply.

`_agent-guidance`'s `article-watch.yml` polls a feed of Anthropic
engineering articles hourly and fires an article-lift routine
(`docs/routines/article-lift.md` there) for each new one about agents. It is
optional. `create-environments.sh` sets the repository variable
`ARTICLE_WATCH_FEED_URL` to `none`, which skips each hourly run with a notice,
so the watch is off until you turn it on: set `ARTICLE_WATCH_FEED_URL` to the
feed's URL (the script never overwrites a value you set) and the next two.

- `ARTICLE_WATCH_FIRE_URL`: a repository variable on `<you>/_agent-guidance`,
  the article-lift routine's fire URL.
- `ARTICLE_WATCH_FIRE_BEARER`: a repository secret on `<you>/_agent-guidance`,
  that routine's bearer.

Whether a script could set each by-hand value, and what fails while it is
unset (checked against the starter workflows):

| Values | A script can set it? | While unset |
|---|---|---|
| `FLEET_WORKER_FIRE_URL`, `FLEET_WORKER_FIRE_BEARER` | No: the routine's API trigger on claude.ai shows them once | Every scheduled Fleet worker fire fails naming the missing one |
| `LOOP_WORKER_FIRE_URL`, `LOOP_WORKER_FIRE_BEARER` | No, same reason | The Loop worker's scheduled fire fails naming it, but only once `EVALS_REPO` names `skills-evals`; while it is `none` the fire is skipped |
| `ARTICLE_WATCH_FIRE_URL`, `ARTICLE_WATCH_FIRE_BEARER` | No, same reason | Nothing while `ARTICLE_WATCH_FEED_URL` is `none` (the watch is skipped); a feed URL turns them on, and the run then fails naming them |
| `PROMPT_AUDIT_SWEEP_FIRE_URL`, `PROMPT_AUDIT_SWEEP_FIRE_BEARER` | No, same reason | Nothing fails: the workflow comments that the fire isn't configured |
| `SITE_PAGE_URL`, `SITE_ASSET_URL`, `SITE_FRESHNESS_ROUTINE_ID`, `SITE_FRESHNESS_FIRE_BEARER`, `SITE_PREVIEW_URL` | No: your website's URLs and a routine's trigger | Nothing while `SITE_REPO` is `none`, which `fleet.env.example` ships; with a site, the site workflows fail naming them |

Every value a script could derive (a plan's cadences, `EVALS_REPO`, the
article watch's `none`, `SITE_REPO` from `fleet.env`) is already set by one.

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

The tests use no network, sleeps, or wall clock. `tests/stubs/gh` is a
stateful stand-in for `gh` that logs every argv and stores secrets only as
SHA-256. The git remotes are local bare repos (`BOOTSTRAP_GIT_BASE`), with a
scratch `HOME` and `GIT_CONFIG_GLOBAL`. The real `copy-starter.sh` copies
all six exports in, the test merges them, and the real `regenerate.sh` runs
each repo's generator on them. `apply-settings.sh` and `install-machine.sh`
run against repos holding a fake engine and fake installers that log their
arguments, and the real engine's `--help` is checked for every flag the
script passes. Run the tests in a PID namespace
(`unshare --pid --fork --mount-proc --`, adding `--user --map-current-user`
when not root).

The suite also runs these checkers:

- `tests/check-refs.py` compares every workflow's variables and secrets with
  the scripts that set them. - `tests/check-branch-prefixes.py` keeps the
  routine prompt, the gates, and the docs on one set of loop branch lanes. -
  `tests/check-guide-lists.py` compares the docs with the workflows, Apps,
  environments, and `REGENERATE.md`. - `tests/check-steps.py` checks
  `steps.json`. - `tests/check-links.py` resolves every relative link and
  anchor in the kit's own pages.
