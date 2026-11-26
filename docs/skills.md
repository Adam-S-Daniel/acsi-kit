# Skills

## The registry

[`acsi-agentskills`](../starter/agent-skills/README.md) is a Claude Code
plugin marketplace (`.claude-plugin/marketplace.json`) with four plugins,
grouped by audience and runtime. `acsi-anything-anywhere` and
`acsi-coding-anywhere` are cloud-safe and enabled by default.
`acsi-coding-local` and `acsi-non-coding-local` are machine-bound and
opt-in. A skill is a folder, `plugins/<plugin>/skills/<skill>/`, holding a
`SKILL.md`, and the same file works in Codex and any agent that reads the
Agent Skills format. A plugin can also carry hooks. `acsi-anything-anywhere`
ships the fleet-guidance fetch and a hook that blocks any APPROVE review and
any GitHub write without the agent marker.

The marketplace has a fifth entry, `example-site-platform`, which shows a
federated plugin served from another repo. Point it at one of your repos or
remove it. Removing it retires the name, so that change needs the review
below.

The kit ships its skills in tiers ([choosing optional
content](#choosing-optional-content)). Four core skills are always in the
registry: `workflow-path-audit`, `skills-doctor`,
`github-actions-repo-settings`, and `vendor-release-impact-issues`. They are
copied unchanged from the owner's registry into `acsi-coding-anywhere`, and
their eval fixtures are in `skills-evals` (`evals/<skill>/`), so the loop
has something to measure on day one. `bootstrap/add-content.sh` adds the
optional ones. The template is `templates/skill/` in the registry (a
`SKILL.md` and a `PURPOSE.md` with `<placeholders>`). It sits outside
`plugins/`, so nothing loads, lists, or locks it. To add your own skill:

1. Copy `templates/skill/` to `plugins/<plugin>/skills/<skill>/`, fill in
   the `SKILL.md`, and use `PURPOSE.md` to record the incident or pattern
   behind it.
2. Add it to `scripts/plugin_layout.json`, the canonical list of which
   plugin ships which skill, and add an entry to `docs/skill-impact.md`.
3. Give it at least one eval fixture in `skills-evals` (`evals/<skill>/`). A
   skill joins the registry only with a green `with_skill` arm
   ([evals](evals-and-loop.md#fixtures)). `workflow-path-audit`'s fixtures
   are the worked example.

Once a skill ships, its folder name is a one-way door: a consumer's
`skills.lock` keys on it, and the marketplace has no `renames` map. The
required `pytest` job enforces this in two ways.
`scripts/check_skill_gates.py` fails a pull request whose new, edited, or
removed `SKILL.md` lacks its `PURPOSE.md`, its `docs/skill-impact.md` entry,
or an eval line. `scripts/check_one_way_doors.py` fails one that removes,
renames, or moves a shipped skill or plugin, or reuses a retired name
(`scripts/shipped_names.json` is the ledger), unless its description ends an
adversarial review with `Adversarial-review: pass <link>`
([`docs/one-way-doors.md`](../starter/agent-skills/docs/one-way-doors.md)).
The registry's `AGENTS.md` says what else each change needs.

**Durable machines** add the marketplace once and get the enabled plugins.
`install-machine.sh` runs the registry's `setup.sh --owner-machine`, which
writes both marketplaces and the plugins into `~/.claude/settings.json`
([machines](machine.md#install-on-each-durable-machine)).

## Choosing optional content

Every skill, guidance section, and git-hook check the kit ships belongs to
one of three tiers, listed in
[`bootstrap/content-catalog.json`](../bootstrap/content-catalog.json):

- **Core**: what the rest of the system depends on. It is always in
  `starter/`, and automatic retirement never removes it
  ([evals](evals-and-loop.md#the-loop)). The loop can remove anything else
  you add, based on its eval verdict or because nobody uses it.
- **Recommended**: what most adopters want. That is two skills
  (`review-bash-ci-reliability`, `disarm-inherited-reach`), four safety
  sections, and three sections on everyday working, pasted-config and git
  habits.
- **Opinionated**: a particular way of working that may not match yours.
  That is two skills (`writing-adrs`, `finding-unknowns`), four guidance
  sections, and the `rules-dir` git hook. Each item's `details` text says
  what it does and when it clashes with how you work.

The optional items live in [`library/`](../library/README.md), each with
everything it needs: the skill folder, section text, or check code, plus its
eval fixtures, weekly schedule rows, eval-coverage row, impact-log entry,
and tests. Step 1 of the quick start adds your choices to your copy of
`starter/`, before any tree is copied to GitHub:

```bash
bash bootstrap/add-content.sh --items recommended --dry-run    # what would change
bash bootstrap/add-content.sh --items recommended,writing-adrs # add them
bash bootstrap/add-content.sh --items none                     # add nothing
```

The script is idempotent and refuses an id the catalog doesn't offer. It
rebuilds the files generated from what it changed (the guidance mirror in
every repo, `AGENTS.md`, the section byte counts, the registry's README
table, and `skills.lock`) and records your choices beside `status.sh`'s
state file. If you run it after the repos exist, it changes only `starter/`
and lists the repos that need a pull request. The `/adopt` skill asks these
questions for you.

## Cloud sessions and skills.lock

A cloud session starts with no plugins. Instead, each repo commits a
`skills.lock` (the registry, an immutable commit, the bundles, and a sha256
per skill) and receives the `skills-bootstrap.sh` SessionStart hook from the
sync. At session start, the hook fetches the locked skills, checks every
digest, and copies them into `~/.claude/skills`. On a durable machine it
does nothing. In a session opened on several repos it installs the union of
every lock, which requires a setup script in the cloud environment ([cloud
environments](machine.md#cloud-environments)).

Until you regenerate them, the exports' locks pin the owner's registry, or
forty zeros in the registries themselves ([the skills
locks](generated-files.md#the-skills-locks)). After that,
`_agent-guidance`'s `skills-lock-bump.yml` uses the `guidance-sync` App to
re-pin every consumer's lock and the hook pin four times a day and, with
evals, whenever your registry's `main` changes.

## Plugin runtime review

A pull request that changes how a plugin runs code (its hooks, `bin/`, a
package install, plugin settings, or a script a hook calls) waits on the
`plugin-runtime-review` environment, which only you can approve ([ADR
0016](../starter/agent-skills/docs/decisions/0016-open-plugin-folders-and-gate-runtime-changes-on-owner-approval.md)).
`plugin-runtime-review.yml` runs on `pull_request_target`, so it judges a
pull request with the base branch's code. Its `detect` job decides whether a
change matters, and an ordinary change passes at once. It publishes the
required `plugin-runtime-approval` check. When a pull request is waiting,
open the waiting job's page, read the change, and approve or reject it
there. Never approve it for an agent.

## The privacy check

The registries' predecessor was retired because its git history contained
personal data. Now `acsi-agentskills`' required `privacy` job scans every
tracked file's path and text, plus a change's commit messages, author
identities, and branch name, against a denylist of your real names, emails,
hosts, and account ids. The list is the repository secret
`PRIVACY_DENYLIST`, never a file in a repo. The script prints only
`file:line` and the pattern's number, never the match, and it fails closed
without the secret, including on a fork's pull request.

In `acsi-agentskills` the secret is required: that job is set up in step 3
and fails closed without it. For the other two scans below it is optional.
With it, each repo's `agent-checks` job also scans a pull request's added lines, commit messages,
branch name, title and body, and the `privacy-comment-alert` workflow scans
issues and comments. Without it, both scan nothing and only add a warning;
neither ever fails a check for a missing secret. `set-secrets.sh` stores it
in `acsi-agentskills` and `_agent-guidance`. For another repo, run
`gh secret set PRIVACY_DENYLIST --repo <you>/<repo> < <file>`.

Write the list to a file outside every repo, with one regular expression per
line, and store it before the `acsi-agentskills` starter pull request:

```bash
bash bootstrap/set-secrets.sh --only privacy --denylist ~/private/denylist
```

The script refuses a path inside a git work tree, checks that every line
compiles, and sends the file to `gh` on stdin. To run the same check
locally, use
`PRIVACY_DENYLIST_FILE=<path> python3 scripts/check_privacy_denylist.py` in
your `acsi-agentskills` clone. Everything in the public repos uses invented
data: `example.com`, made-up names, and `<user>` placeholders.

## The private registry and lessons

[`acsi-agentskills-private`](../starter/agent-skills-private/README.md) is
packaged the same way, for skills that are personal rather than reusable.
Its `persistent/lessons` branch holds the lesson records the session miner
writes from your transcripts on your machine
([machines](machine.md#scheduled-jobs-wsl-automation)). With evals,
`skills-evals`' daily draft lane reads them with the `registry-read` App,
ranks them alongside the `skill-proposal` issues you file in
`acsi-agentskills`, and turns one proposal a day into a draft skill or, when
a check would do, a hook proposal ([evals](evals-and-loop.md#the-loop)).
