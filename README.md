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
