# Real GitHub Free walk

A maintainer's test, not an adopter's step: walk the kit's base track as an
adopter on GitHub Free would, against real GitHub, with a second account. The
fake-gh walk in `bootstrap/tests/` cannot see the App manifest flow and
installs in a browser, rulesets, auto-merge and environments on a Free
account's private repos, Actions on a young account, scheduled-workflow
failures and the emails they send, or the Actions minutes used. This folder
holds what a rerun needs: this checklist, `walk.sh` (the wrapper every command
goes through) and `walk.env.example` (its settings). Everything that names the
test account stays outside the repo.

Out of scope: the Claude side (the test runs on the maintainer's own Claude
plan), the evals track, and every claude.ai step. Mark those by hand with
`status.sh --mark N`, and leave the fire URLs at `none`.

## Before starting

1. **Kit version.** Walk the head of `main` once every open fix the walk is
   meant to check has merged. Record the sha.
2. **GitHub's terms** (Terms of Service, B.3) allow one person no more than
   one free account, and no accounts registered by bots. So:
   - The maintainer's main account stays on a paid plan for the whole test.
     Check Settings, Billing and plans, first.
   - If the maintainer already has a free second account, use it: do not make
     another. Check the account switcher (`github.com/logout` lists every
     account signed in to that browser).
   - Otherwise the maintainer registers the new account. An agent may fill in
     the form, but the maintainer sets the password, solves the puzzle, clicks
     the final button and enters the email code. GitHub only starts a sign-up
     while the browser is signed out of GitHub, or in a separate browser
     profile.
3. **Email.** One the maintainer can read, kept out of every repo, issue,
   commit and log. Call it "the test account's email" in notes.
4. **Login.** Neutral: nothing that names the maintainer or their computer.
   App names come from `APP_NAME_PREFIX` (default: the login).
5. **No paid features.** Never add a payment method, start a trial or buy
   anything on the test account. With no payment method, Actions on private
   repos stop at the included amount instead of billing.
6. **Name clashes.** `create-repos.sh` wants `repo-settings` and
   `acsi-agentskills-private` private. A public fork with either name on the
   test account cannot be made private: rename it first (Settings, General),
   and rename it back at teardown.

## Setup

On the computer that runs the commands, with `gh`, `jq`, mikefarah `yq` v4,
`python3` (with PyYAML), `git`, `node` and `claude` installed:

```bash
W=/path/to/acsi-free-walk            # not inside any git repo
mkdir -p "$W/home/repos"
git clone https://github.com/<kit-owner>/acsi-kit.git "$W/kit"
cp "$W/kit/export/real-free-walk/walk.env.example" "$W/walk.env"   # fill it in
cp "$W/kit/bootstrap/fleet.env.example" "$W/fleet.env"            # fill it in
export REAL_WALK_ENV="$W/walk.env"
walk() { "$W/kit/export/real-free-walk/walk.sh" "$@"; }
walk true; echo $?                   # 3: refuses, gh not signed in there yet
```

`fleet.env` for the walk: `OWNER` and `OWNER_TWO` the test login,
`OWNER_TYPE=user`, `PLAN=free`, `CLAUDE_PLAN` the maintainer's plan,
`TIME_ZONE`, `OWNER_NAME` the test login (never a real name),
`REPOS_DIR=$W/home/repos`, the rest empty.

Build the walk's denylist at `$W/home/denylist.txt` (mode 600) from the
maintainer's own privacy denylist, plus the test account's email and the
computer's name, so step 3's scan catches a leak of the maintainer's data
into the test repos. Never print it.

Then, with the test account signed in to the browser (read the login on the
page before every write; a write as the maintainer is the worst outcome):

```bash
walk --auth gh auth login --web -s repo,workflow   # enter the code at github.com/login/device
walk --auth gh auth setup-git
walk gh extension install github/gh-actions-lock
walk bash "$W/kit/bootstrap/preflight.sh" --config "$W/fleet.env"
```

Prefer a browser profile signed in only to the test account. In a shared
profile, use GitHub's account switcher.

## Steps

Run each script with `--dry-run` first, then for real, as
`docs/quick-start.md` says, every command through `walk` and with
`--config "$W/fleet.env"`. After each step, run
`walk bash "$W/kit/bootstrap/status.sh" --config "$W/fleet.env" --track base`.
Merge starter pull requests as the test account
(`walk gh api -X PUT repos/<login>/<repo>/pulls/<n>/merge -f merge_method=merge`)
after reading their workflow runs. For each step, record what the docs
predicted and what happened.

What to watch:

- **2 create-repos:** private repos on Free, labels, default branch, and any
  name clash (Before starting, item 6).
- **3 set-secrets:** use `$W/home/denylist.txt`; record whether it refuses
  any line.
- **4, 10, 12, 13 starter pull requests:** do workflows start on the first
  pull request, is there an "approve and run" prompt, which checks are red,
  and do they match `docs/settings-and-apps.md`, "Merging the starter pull
  requests".
- **5, 8 create-environments:** environments on public repos; none on
  private ones on Free.
- **6, 7 Apps:** open the manifest page `create-apps.sh` writes in the test
  account's browser, click Create, and paste the `127.0.0.1/?code=...` URL
  into the script's prompt within the hour. Never write the code anywhere
  else. Install each App on the repos it names; record whether a private App
  installs on private repos on Free, and whether step 7 needs the manual mark.
- **14 to 18 regenerate:** pull requests open and merge.
- **20 apply-settings:** each setting's result on the private repos
  (rulesets' HTTP status, auto-merge, fork approval, secret scanning, CodeQL
  default setup on public repos); then
  `walk bash "$W/kit/bootstrap/verify.sh" --config "$W/fleet.env" --only settings`.
- **21 install-machine:** only through `walk`, so it writes under
  `$W/home`. Record what it cloned and wrote under `$W/home/.claude/`.
- **22, 23, 27 to 30:** mark by hand.
- **End:** `verify.sh --track base` and `status.sh --track base`; record
  the counts and exit codes.

Then let it run for one to two days: read the test account's email for
GitHub's failure notices (which workflows, how often, startup failures
included), and Settings, Billing and plans, Usage for Actions minutes.

## Record

Keep the record outside the repo: one line per step (predicted, seen), then
the findings ranked by how badly each would stop an adopter. A fix goes
through the usual kit process (a branch off `main`, a pull request, review).
Findings filed in a public repo say "the Free test account", never its login
or email.

## Teardown

Within two weeks, and after the fixes merge:

1. Disable every scheduled workflow in the test repos
   (`walk gh api -X PUT repos/<login>/<repo>/actions/workflows/<id>/disable`),
   so the failure emails stop.
2. Uninstall the Apps from the test account, then delete each App (Settings,
   Developer settings, GitHub Apps, Advanced).
3. `walk --auth gh auth refresh -s delete_repo`, then delete the test repos.
   Rename back anything renamed in Before starting, item 6.
4. An account made for the walk is deleted by the maintainer (Settings,
   Account); an existing second account stays.
5. `rm -rf "$W"`: it holds the test account's gh token.

## Privacy

None of these go into the test repos, their commits, pull requests, issues,
logs, App names or descriptions: the maintainer's name, email addresses and
mail domain, the test account's email, the computer's name, local user paths,
and the maintainer's own login. Commits use the test account's noreply
identity (`walk.sh` sets it). No collaborator invites, App installs or
claude.ai GitHub connection link the two accounts.
