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
cp bootstrap/fleet.env.example fleet.env   # fill in OWNER, OWNER_TWO, PLAN, CLAUDE_PLAN
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
`~/kit-starter-backup-<commit>` (a patch, `starter-edits.patch`, and a copy of
the new files, `new-files/`). Your own `starter/` edits belong in a pull
request on your repo after `copy-starter.sh`, not in the kit. Your content
choices are recorded outside the kit. Your `fleet.env` and your app manifests
folder are untouched.

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
