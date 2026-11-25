<!-- Managed by _agent-guidance: built by scripts/build-contributor-rules.js
     from agents-md/base.md (the sections agents-md/eval-coverage.yml marks
     audience: contributor). Do not edit here; the next sync overwrites it. -->

# Fleet contributor rules

These rules apply to anyone, person or agent, changing this repository. They
are the contributor half of the fleet guidance kept in
[`_agent-guidance`](https://github.com/example-adopter/_agent-guidance). Read
them before non-trivial work when the full guidance did not load in your
session.

## Working in these repos

- **An issue or PR labeled `on-hold` is paused by the owner.** Do not work on
  it (no commits, reviews, merges, closing or follow-ups that do it); read,
  cite and list it as on hold without asking again. A held PR stays open.
  Only the owner adds or removes the label, or an agent the owner directs in
  that session.

## Data exposure in CI and public repos

CI logs, summaries, artifacts, run pages and git history are public on a
public repo.

- **Never print personal or sensitive data to a log** — emails, contacts,
  names, IDs, mailbox counts, tokens. Deliver results out-of-band (email the
  account itself); log a non-identifying status.
- **Don't interpolate `${{ inputs.* }}` / `${{ github.event.* }}` into a
  `run:` block** — the rendered command is echoed. Read inputs from
  `$GITHUB_EVENT_PATH`; `::add-mask::` sensitive values first.
- **Sensitive config goes in secrets**, not inputs or `vars`.
- **Sanitize error output** — never dump an API/HTTP body; log a status code
  plus error type, the data-bearing call inside the try/catch.
- **Least privilege:** minimal `permissions:` (usually `contents: read`);
  require approval for outside-collaborator fork PRs.
- **Fixtures use `example.com` / `example.net` only.**
- **Sanitize before the first commit.** Committed sensitive data means
  rewriting history, deleting every ref to it (branches, tags, PRs) and
  force-pushing — the one sanctioned force-push.
- **Commit with the `…@users.noreply.github.com` identity** on public repos.

## Automation vs branch protection

Fleet repos are PR-only on the default branch via ruleset, managed in
`repo-settings` (ADR 0001).

- Never design a bot that pushes to a protected default branch — rejected
  (GH013), even from its own workflows.
- Generated data goes on an unprotected results branch (skills-evals'
  `persistent/eval-results`), treated as untrusted.
- **A branch that outlives its PRs is `persistent/<purpose>`** (results,
  routine accumulation), guarded by a per-repo deletion-only
  `extra_rulesets` entry on `persistent/**` in `fleet.yml` (repo-settings
  ADR 0007). Never delete one; stale-branch cleanups skip the prefix.
- A bot that must write to a default branch needs a ruleset bypass actor
  declared in repo-settings' `fleet.yml`, never
  a hand-granted UI bypass.
- PR + auto-merge is a sanctioned bot-write path only where a repo-settings
  ADR declares the exception: the eval and guidance loops' PRs (ADRs 0003,
  0012, 0014), lesson-check PRs (0013) and the changelog routine's (0015);
  example-site-platform-managed repos use it by design.
- **A required status check gets no `concurrency` group** when its job can
  fire twice on one head sha (label events, `opened` + `synchronize`): a
  cancelled run can win the context and block the merge for good.
  `cancel-in-progress: false` does not help (only the latest pending run
  survives), a shared group cancels older siblings, so make triggers pairwise
  disjoint; `push`/`synchronize`-only jobs may keep `cancel-in-progress:
  true`. Lock it with a test that parses the YAML.
- **Every CI job on pull requests is a required check** unless the repo's
  `AGENTS.md` documents why not. Ship the job and its ruleset change in one
  PR (`PUT` checked-in ruleset JSON; read back what is live).
- **Every `pull_request`/`push` workflow filters on its salient paths**
  (`/acsi-coding-anywhere:workflow-path-audit`); update them when a step or
  dependency moves; table them in the repo's `AGENTS.md`.
  **A required check cannot use `on.paths`** — a missing check blocks the
  merge. Keep the trigger broad, detect salient changes in an early step,
  gate every later step on its output: the job still reports success.

## PR descriptions open with a TLDR

Start every PR description with a `## TLDR` heading and one to three
plain-English sentences on what changes and why; only an attribution block
may precede it (`agent-checks` enforces it).

## A successful `git push` does not mean your commit exists

A pre-commit hook that refuses the commit does not stop the push: `git push`
pushes the base commit and prints an ordinary success. The
fleet's `secrets-scan` guard (example-site-platform's `dev-hooks-sync.yml`) FAILS
CLOSED without `gitleaks` on `PATH`, which a fresh container lacks.

- **Verify the commit, not the push:** `git log --oneline -1` shows your
  message and `git status --short` is clean, or `git rev-parse HEAD` differs
  from `git rev-parse origin/<base>`.
- **`&&`-chain commit into push**; a newline or `;` lets a refused commit
  become a pushed branch.
- **Install the tool; skip the bypass.** `SKIP_SECRETS_SCAN=1` is for
  emergencies; the binary is one `curl` away.
- **A push can carry the WRONG ref while both checks pass.**
  `git push -u origin <name>` pushes the LOCAL branch of that name, maybe
  not the one you are on (the commit lands on `main` and the push
  updates a stale local branch). The only check naming commit AND
  remote branch: `git merge-base --is-ancestor <sha> origin/<branch>`, after
  every push.

## Pinning GitHub Actions

**Two forms while repos migrate** ([ADR 0024](https://github.com/example-adopter/_agent-guidance/blob/main/docs/decisions/0024-actions-pin-through-lockfiles.md)):

- **Lockfile, the target:** `.github/workflows/actions.lock` covers every
  workflow; each `uses:` on its most exact tag, by hand; local actions
  `$/<path>`, not `./`. Then `gh actions-lock --no-narrow`. Repos where actionlint
  meets `$/`, or with `./` refs into a runtime checkout (`example-site-platform`),
  stay legacy.
- **Legacy:** full 40-hex SHA, no trailing version comment.
- **Cross-repo reusable workflows take a full SHA in both forms**; no lockfile
  covers them.
- **The runner runs whatever commit the lockfile names**, even off-tag:
  require `Adam-S-Daniel/verify-actions-lock` (fails on a pin error) and
  the Require lockfile policy. Review `actions.lock` as pins.
- **Wait 7 days after a third-party release**, else pin the previous.
- **Dereference annotated tags:** `git ls-remote <url> 'refs/tags/<tag>^{}'`.
- **The one carve-out:** `example-site-platform` refs stay on its release tag.

`sha_pinning_required: true` stays on; a locked tag satisfies it.

## Git practices

- **Merge with a merge commit — `gh pr merge --merge`.** Squash and rebase
  are off (`--squash` fails; do not offer it). Squash strands commits a
  lockfile pins by sha (`cannot resolve ref`).
