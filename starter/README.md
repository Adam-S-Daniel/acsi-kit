# The six exports

Each folder here is an export of one of the owner's real repos at a pinned
commit, with every owner name replaced by an invented one, the owner's own
content left out, and the generated files rebuilt.
[`../export/`](../export/DECISIONS.md) holds the machinery: a manifest per
repo (`export/manifests/`), the patches and overlays, and `export.py`, which
rebuilds these folders from the source repos. `export.py --check` fails if a
folder differs from a fresh export by even a byte, so don't edit a folder by
hand. Change its manifest, patch, or overlay and export again.

| Folder | Goes into | What it is |
|---|---|---|
| [`agent-guidance/`](agent-guidance/README.md) | `<you>/_agent-guidance` | The fleet guidance, the sync that delivers it, the hooks, templates and agent-checks runner, and the routine specs ([guidance](../docs/guidance.md)) |
| [`repo-settings/`](repo-settings/README.md) | `<you>/repo-settings` | Every repo's settings as code (`repo-settings/fleet.yml`) and the engine that applies them ([settings](../docs/settings-and-apps.md)) |
| [`agent-skills/`](agent-skills/README.md) | `<you>/acsi-agentskills` | The skills registry: a plugin marketplace with four empty plugins, the privacy check and the plugin runtime review ([skills](../docs/skills.md)) |
| [`agent-skills-private/`](agent-skills-private/README.md) | `<you>/acsi-agentskills-private` | The private registry, packaged the same way; its `persistent/lessons` branch holds the session miner's lessons |
| [`skills-evals/`](skills-evals/README.md) | `<you>/skills-evals` | The eval harness, the planner, the gates and the lanes of the loop ([evals](../docs/evals-and-loop.md)) |
| [`wsl-automation/`](wsl-automation/README.md) | `<you>/wsl-automation` | The jobs that run on your machine: the session miner, the usage census, the waiting feed ([machines](../docs/machine.md#scheduled-jobs-wsl-automation)) |

`../bootstrap/copy-starter.sh starter/<folder> <you>/<repo>` copies one in
through a pull request and gives it your names. A few generated files keep a
placeholder or the owner's value until you rebuild them on your account.
[`../export/REGENERATE.md`](../export/REGENERATE.md) lists them, and
[generated files](../docs/generated-files.md) says which step handles each.

## Running the tests

```bash
unshare --user --map-current-user --pid --fork --mount-proc -- bash run-all-tests.sh
```

As root, use `unshare --pid --fork --mount-proc --`. `known-failures.txt` is
calibrated for that form. Under the mapped user namespace as root, some ids
report as `ERROR` instead of `FAIL`, so they aren't excused.

The command runs each export's suite through `../export/run_suites.py`. That
script copies the folder to a temporary directory, makes it a git repo where
the suite reads its history, runs the repo's setup and test command in a PID
namespace, and prints one PASS or FAIL line per folder and form. The five
base folders run three times: as exported (`--owners invented`), with one
owner (`one`), and with two other owners and the example repos dropped
(`two`), the way `copy-starter.sh` leaves an adopter's tree; `skills-evals`
runs as exported only. Each suite needs
what its repo's CI installs, and the manifest's `suite.needs` lists it.
`RUN_ALL_FORMS=one` (or any of the three, separated by spaces) runs only
those forms, which is how the kit's CI runs one form per job.
Up to six runs start at the same time (`RUN_ALL_JOBS`), so a suite whose setup installs Python
packages (`skills-evals`) runs in its own virtual environment, created under
its temporary directory and deleted with it. Its pins, which differ from
`agent-skills`' and `repo-settings`', never replace a package another suite
is importing, and your own interpreter's packages are left as they were.
`_agent-guidance`'s suite needs mikefarah's Go `yq` v4 on `PATH`. Debian's
`yq` is a different program, and with it `scripts/sync.sh` refuses to run,
so about 250 of that suite's assertions fail. The `skills-evals` suite takes
the longest, about five minutes on four cores and much longer on two. To run
it alone, in the background with a log, use
`python3 ../export/run_suites.py --kit-name skills-evals`.

[`known-failures.txt`](known-failures.txt) lists failures caused by the
machine running the tests rather than by the kit, each with its exact test
id and the reason. `run-all-tests.sh` passes a folder whose failures are all
on that list and names each one it excused. Any unlisted failure still
fails. Read the exit code directly, not through a pipe.

CI runs these suites in the `starter-suites` job of
[`ci.yml`](../.github/workflows/ci.yml) on any pull request or push that
changes `starter/` or `export/`.
