# Adopt the whole self-improvement system

This kit builds the system I run on your own GitHub account and Claude plan:
fleet guidance delivered to every surface and deduplicated in multi-repo
sessions, a skills registry, git-hook checks, centralized memory, evals, a
loop that improves and retires skills and guidance, and public and private
dashboards.

It contains working exports of the six repos that run the system, with every
owner name replaced, plus scripts that create your repos, settings,
environments, and GitHub Apps and copy each export in through a pull
request.

## Start here

Clone this repo and run Claude Code in the clone:

```bash
git clone https://github.com/Adam-S-Daniel/acsi-kit.git
cd acsi-kit
claude
# then, in the session:
/adopt
```

Clone it outside any other git repository. Claude Code loads every
`CLAUDE.md` from the folder it starts in and each folder above it, plus
`.claude/settings.local.json` at the root of the repository it starts in.
This repo deliberately has none of those, so only the `/adopt` skill and
your own `~/.claude/` apply. Inside another repository, that repository's
rules would load too. (Checked with Claude Code 2.1.312 on 2026-10-29, and
against its memory and settings docs.)

The [`/adopt` skill](.claude/skills/adopt/SKILL.md) checks where your
account stands, explains the next step, and runs each script with you, dry
run first. It sets up the base: guidance, the skills registries, repo
settings, git hooks, and your machines. The [`/adopt-evals`
skill](.claude/skills/adopt-evals/SKILL.md) adds evals, now or later. From a
fresh start it runs the base first, so one command can set up everything.
Without evals, nothing measures, improves, or retires your skills and
guidance automatically ([with or without
evals](docs/before-you-start.md#with-or-without-evals)).

## Without Claude

`bootstrap/status.sh` gives you the same walkthrough in a terminal: every
step, which ones are done (it checks GitHub rather than a list you keep),
and what to run next.

```bash
cp bootstrap/fleet.env.example fleet.env   # fill in OWNER, OWNER_TWO, PLAN, CLAUDE_PLAN, TIME_ZONE
bash bootstrap/preflight.sh
bash bootstrap/status.sh
```

Add `--track base` to see only the steps without evals.
[docs/quick-start.md](docs/quick-start.md) lists every step. Hands-on setup
takes one to two days, mostly in the browser. With evals, the loop's first
merged improvement comes one to two weeks later, because it waits on the
eval budget rather than on you ([what it
costs](docs/before-you-start.md#what-it-costs)).

## Update your copy of the kit

The kit changes often. To move your clone to the newest kit, open a terminal
in the kit's folder and paste this block. The same block works for every copy,
including one made before `bootstrap/update-kit.sh` existed: it fetches the
newest kit and runs the newest `update-kit.sh` from a temporary folder. If your
`fleet.env` is not in the kit's folder, put its path in the first line in
place of `./fleet.env`.

```bash
cfg=./fleet.env
git fetch origin &&
tool=$(mktemp -d) &&
git archive origin/main bootstrap | tar -x -C "$tool" &&
bash "$tool/bootstrap/update-kit.sh" --kit . --config "$cfg"
```

Nothing in the block changes your clone; only the last line's script does,
and it refuses, changing nothing, when you have edited a tracked file outside
`starter/`, edited `starter/` yourself, when it cannot find your `fleet.env`,
or when your `fleet.env` does not load under the newer kit (it names the key
to fix). To see its plan first, add ` --dry-run` to the last line; when it
refuses your own `starter/` edits, add ` --discard-starter-edits` there to
save them and go ahead. It
fast-forwards your clone, puts the optional content you chose back, and lists
the `fleet.env` keys that are new (saying which are required) or gone. It
exits 0 only when everything worked; then run what it prints last,
`bash bootstrap/status.sh` (with your `--config`).

If it stops, it says what changed and what to run next; once you have done
that, paste the block again. Before it discards anything under `starter/` it
saves all of it, your own edits and new files included, to a new folder
`~/kit-starter-backup-<commit>` (a patch named starter-edits.patch, and a copy
of the new files in a folder named new-files). Your own `starter/` edits belong in a pull
request on your repo after `copy-starter.sh`, not in the kit. Your content
choices are recorded outside the kit. Your `fleet.env` and your app manifests
folder are untouched.

Before and after the update it runs `bash bootstrap/status.sh` (read-only)
and lists any setup step that was done before and is not done under the
newer kit, because its check now covers more, with the command to run again.
It also lists new `fleet.env` keys; a key only a later script needs, such as
`TIME_ZONE` (needed by `copy-starter.sh`), is named with the step that needs
it and does not stop the update. These steps changed recently for a setup
that already ran them:

- Step 2 (the repos): `create-repos.sh` now also creates a `ci` label, so
  step 2 shows as not done until you run `bash bootstrap/create-repos.sh`
  again (it skips what exists).
- Steps 8 and 37 (the repository variables): run
  `bash bootstrap/create-environments.sh` again. It sets
  `LOOP_WORKER_EVERY_HOURS` to your plan's value (replacing one you set by
  hand), adds `EVALS_REPO` to the `acsi-agentskills` registry, and writes
  `none` to `FLEET_WORKER_FIRE_URL` and `LOOP_WORKER_FIRE_URL` if they are
  not set (a URL you set is kept).
- Steps 7 and 34 (installing the Apps): `gh` cannot read App installations,
  so check each App's installation page, then mark the step yourself:
  `bash bootstrap/status.sh --mark 7` (and `--mark 34`).
- Step 27 (the fleet worker routine): done only when `_agent-guidance` has
  both `FLEET_WORKER_FIRE_URL` (not `none`) and `FLEET_WORKER_FIRE_BEARER`.
- Step 3 (the privacy denylist): `set-secrets.sh --only privacy` now stores
  it in four repos (the registry, `_agent-guidance`, `repo-settings`,
  `wsl-automation`), so a setup that stored it before shows step 3 as not
  done again. Run step 3 again; it skips the repo that already has it.
- Step 3, and your own commits: the kit's own commits (`copy-starter.sh`,
  `regenerate.sh`) now use `OWNER_NAME` and your GitHub noreply address,
  not git's own `user.name` and `user.email`. Commit in these repos under
  the same identity ([the privacy check](docs/skills.md#the-privacy-check)
  says how; `bash bootstrap/preflight.sh` warns until you do), and keep
  the list at `~/.config/privacy-denylist.txt`, where this machine's checks
  read it (`bash bootstrap/install-machine.sh` warns while it is missing).
  Commits already made keep the identity they were made with.
- Steps 12 and 20 (the registry's `privacy` job): the `acsi-agentskills`
  starter no longer has its own `privacy` CI job, and `fleet.yml` no longer
  requires it; each repo's `agent-checks` scans for personal data instead
  ([the privacy check](docs/skills.md#the-privacy-check)). If you copied
  the registry and applied `fleet.yml` with an older kit, first remove
  `privacy` from `acsi-agentskills`' `required_status_checks` in your
  `repo-settings/fleet.yml` and apply it: on `PLAN=paid`, approve the
  `fleet-apply` deployment its merge starts; on `PLAN=free`, run
  `bash bootstrap/apply-settings.sh` (step 20). Only then take the newer
  starter's `.github/workflows/ci.yml` into your registry (`copy-starter.sh`,
  below). In the other order, the registry's pull requests wait on a
  `privacy` check that nothing reports.
- Step 0 (fleet.env): while `TIME_ZONE` is empty and a base step that runs
  `copy-starter.sh` is still open, step 0 shows as not done again; set
  `TIME_ZONE` in your `fleet.env` (the update names it as a new key and
  shows the same reason).
- Step 35 (creating `skills-evals`, on the evals track): it now also stores
  the privacy list in `skills-evals`. If you created it before, run
  `bash bootstrap/set-secrets.sh --only privacy --denylist <the same file>`
  again; it stores only the copy that is missing.
- Step 22 (the machine jobs): `~/.config/wsl-automation/settings.env` now
  needs `WSL_AUTOMATION_AGENT_OWNER_ROOTS`, the folder that holds your clones
  (on Windows, a user environment variable of that name instead;
  [machine](docs/machine.md#scheduled-jobs-wsl-automation) has the details).

On macOS, if it says it needs bash 4.4 or later, install it (`brew install
bash`) and replace `bash` at the start of the last line with
`"$(brew --prefix)/bin/bash"`; nothing was changed before that check.

It does not change repos you already filled from an older starter. For
those, `bash bootstrap/copy-starter.sh --dry-run <starter-subdir> <owner/repo>`
shows what the newer starter would change.

## Read more

- [How it works](docs/how-it-works.md): the six repos, the loop, and the
  rules the design follows.
- [Before you start](docs/before-you-start.md): what you need, what it costs,
  `fleet.env`, one owner or two.
- The parts, one page each: [settings and Apps](docs/settings-and-apps.md),
  [guidance](docs/guidance.md), [skills](docs/skills.md),
  [generated files](docs/generated-files.md),
  [evals and the loop](docs/evals-and-loop.md),
  [routines](docs/routines.md), [machines and cloud](docs/machine.md).
- [Week to week](docs/week-to-week.md) and [traps](docs/traps.md).
- [`bootstrap/`](bootstrap/README.md): what each script does and cannot do.
- [`starter/`](starter/README.md): the six exports. How they were made and
  what was left out: [`export/DECISIONS.md`](export/DECISIONS.md).
- [`library/`](library/README.md): the optional skills, guidance and git
  hooks you can add before the first copy
  ([choosing optional content](docs/skills.md#choosing-optional-content)).

## Test the kit

```bash
# as an ordinary user:
unshare --user --map-current-user --pid --fork --mount-proc -- bash run-all-tests.sh
# as root (a mapped user namespace leaves `nobody` unmapped, which breaks the
# tests that drop privileges):
unshare --pid --fork --mount-proc -- bash run-all-tests.sh
```

`run-all-tests.sh` runs every export's test suite, the bootstrap tests, the
export's own tests (the leak scan, and a check that git tracks every kit
file), and `export/export.py --check`, printing one PASS or FAIL line for
each. `starter/known-failures.txt` is calibrated for the root form, so a few
ids differ when you run as an ordinary user. The export check needs the
source repos checked out beside the kit's repo, so a copy of the kit prints
SKIP. Read the exit code directly, not through a pipe. The [starter
README](starter/README.md#running-the-tests) says what each suite needs, how
to run one on its own, and which failures are known.

## License

Apache License 2.0 ([`LICENSE`](LICENSE)). The five public exports carry
their own `LICENSE`.
