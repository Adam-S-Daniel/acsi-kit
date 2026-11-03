---
name: adopt-evals
description: Guide the user step by step through adding evals to this kit's system on their own GitHub account (the skills-evals loop's eval runner routine, its secrets and Apps, the eval fixture default, the optional federation and dashboard), driven by bootstrap/status.sh --track evals, after checking the base is in place. From a fresh start it runs the base steps first, so it also sets up the whole system in one go. Use when the user types /adopt-evals, asks to add or continue setting up evals or the improvement loop, or wants the whole system including evals. For guidance and skills alone, use /adopt.
---

# Add evals, one step at a time

You are helping the user add evals to the system from this kit: the eval
runner routine in `skills-evals`, the secrets and Apps it needs, and the
loop that measures skills and guidance and improves or retires them.
`bootstrap/steps.json` puts each step on the `base` or the `evals` track;
the evals steps are this skill's. The base track is `/adopt`'s, in
`.claude/skills/adopt/SKILL.md`. Work from the kit's folder (the one holding
`bootstrap/`).

## First: is the base in place?

1. Run `bash bootstrap/status.sh --track base` (with `--config <path>` if
   needed). Its last lines say `base: N of M done` and the next base step.
2. If a required base step is not done, the evals cannot work yet: the eval
   steps need the repos, the environments, the Apps and the applied
   settings the base sets up. Say so, then read
   `.claude/skills/adopt/SKILL.md` and follow it, from its "First sitting",
   until `bash bootstrap/status.sh --track base` reads
   `Next: nothing; every required base step is done`. Skip its last step
   (telling the user `/adopt-evals` comes later): you are already here.
   This is how a fresh start sets up the whole system in one command.
3. Once the base is done, say what evals cost before the first eval step:
   `docs/before-you-start.md`, "What it costs" and "With or without
   evals". Evals spend part of the plan's weekly allowance (the cap is in
   `skills-evals`' `evals/budget.yml`; help the user set their own numbers
   there in a pull request before the weekly planner first runs), and the
   first improvement lands one to two weeks after the first eval runs.

## Each turn

Follow `/adopt`'s "Each turn" section, with `--track evals` wherever it
says `--track base`: run `bash bootstrap/status.sh --track evals`, explain
the next step and link its `Read:` section, do it by its kind (dry run
first for a script), then close it by its check type. Only an **`ask`**
step is marked by hand: run `bash bootstrap/status.sh --mark <id>` once the
user says it is done. A `verify` step is never marked: status.sh refuses
`--mark` for it, so run `bash bootstrap/status.sh --track evals` again
until it reads done. The browser steps that create or install the eval
Apps (33, 34) and the federation step (26) are `verify` steps.

When status.sh reads `Next: nothing; every required evals step is done`,
run `bash bootstrap/verify.sh` for the whole setup and show its result.

## Steps with a catch

- **Step 19** (eval.yml's default fixture): the shipped default runs as it
  is; a change is a pull request on the user's `skills-evals`.
- **The eval runner** (steps 24 and 25): the bearer is shown once. The
  user keeps it and the `trig_...` id and types both into
  `set-secrets.sh --only routine-fire` themselves.
- **Steps 26 and 32** are optional: offer them, and move on when the user
  declines.
- **Steps 33 and 34** (`create-apps.sh eval-improve registry-read`, then
  the installations): `create-apps.sh` wants the URL GitHub redirects to,
  so it runs in the user's own terminal.

## Never

- Never approve a deployment, an environment review or a pull request
  review, and never merge a pull request for the user. The
  `plugin-runtime-review` and `fleet-apply` approvals are the owner's alone.
- Never skip, weaken or edit a check, a ruleset or a test to make a step
  pass.
- Never mark a step done the user has not confirmed, and never mark one to
  move past a failure.
- Never print, paste or ask for a secret in the chat. `set-secrets.sh` and
  `create-apps.sh` read secrets from a hidden prompt, a file or a pipe; let
  the user type them there.
