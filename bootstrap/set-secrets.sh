#!/usr/bin/env bash
# set-secrets.sh [--config fleet.env] [--dry-run] [--rotate] [--denylist PATH] [--only privacy|routine-fire]
#
# Sets the secrets and variables the exported workflows read that are not App
# credentials (create-apps.sh stores those). OTHER_VALUES in lib/common.sh:
#
#   acsi-agentskills  (repository)  secret   PRIVACY_DENYLIST          group privacy
#   _agent-guidance   (repository)  secret   PRIVACY_DENYLIST          group privacy
#   repo-settings     (repository)  secret   PRIVACY_DENYLIST          group privacy
#   wsl-automation    (repository)  secret   PRIVACY_DENYLIST          group privacy
#   skills-evals      (repository)  secret   PRIVACY_DENYLIST          group privacy
#   skills-evals      routine-fire  secret   EVAL_ROUTINE_FIRE_BEARER  group routine-fire
#   skills-evals      routine-fire  variable ROUTINE_TRIGGER_ID        group routine-fire
#
# PRIVACY_DENYLIST feeds the privacy scan in the agent-checks CI job of
# acsi-agentskills, _agent-guidance, repo-settings and wsl-automation, the
# only guard against personal data on the base track's public repos. The scan only warns
# where the secret is missing, so nothing fails without it; set it before
# the first starter pull request anyway, so the scan reads every starter
# file the pull requests add. skills-evals' required `test` job scans
# with it and fails closed without it, so the evals track stores it there
# once the repo exists (step 35: run --only privacy again); while
# skills-evals does not exist, its entry is skipped with one line. It is a file OUTSIDE every
# repo, one regular expression per line, matched in any letter case (your real
# name, emails, hosts and private ids); blank lines and lines that start with #
# are skipped. The script refuses a path inside a git work tree, and a pattern
# that matches a public name the starter writes into its files (fleet.env's
# OWNER, OWNER_TWO, OWNER_NAME, REVIEWER and APP_NAME_PREFIX, the logins'
# upper and snake forms, and the Apps' <prefix>-<app> names): every scan that
# reads the list would then fail on every pull request. It never prints a
# pattern, only line numbers. docs/skills.md, "The privacy check", says what the check
# reads and shows a sample file.
#
# The bearer and the trigger id come from the eval runner routine's API
# trigger at claude.ai/code/routines (skills-evals docs/routine/eval-runner-prompt.md);
# the bearer is shown once. routine-eval-fire.yml reads both from the
# routine-fire environment and refuses a trigger id that is not trig_...
#
# Values reach gh on stdin only and are never echoed. --only <group> sets one
# group (privacy comes long before the routine exists).
#
# Idempotent: a value that already exists is left alone (GitHub cannot show a
# secret, so it is not compared); --rotate replaces them. PLAN=free skips
# environments in private repos. Needs: gh, jq, python3.

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"

ROTATE=0 DENYLIST="" ONLY=""
parse_common_args "$@"
set -- "${REST_ARGS[@]}"
while [ $# -gt 0 ]; do
  case $1 in
    --rotate) ROTATE=1; shift ;;
    --denylist) [ $# -ge 2 ] || die "--denylist needs a path"; DENYLIST=$2; shift 2 ;;
    --only) [ $# -ge 2 ] || die "--only needs an environment"; ONLY=$2; shift 2
      [[ $ONLY == privacy || $ONLY == routine-fire ]] || die "--only takes privacy or routine-fire" ;;
    *) die "unknown argument: $1" ;;
  esac
done
require_tools jq python3 "$GH"
load_config "$CONFIG"
O=$CFG_OWNER

BEARER="" TRIGGER="" HAVE_BEARER=0 HAVE_TRIGGER=0 HAVE_DENYLIST=0

get_bearer() {
  [ "$HAVE_BEARER" = 1 ] && return 0
  printf 'EVAL_ROUTINE_FIRE_BEARER (the API trigger token from claude.ai/code/routines; input hidden): ' >&2
  IFS= read -rs BEARER || die "no value given"
  printf '\n' >&2
  [[ $BEARER =~ ^[[:graph:]]{16,4096}$ ]] || die "that does not look like a bearer token (16+ printable characters, no spaces)"
  HAVE_BEARER=1
}

get_trigger() {
  [ "$HAVE_TRIGGER" = 1 ] && return 0
  printf 'ROUTINE_TRIGGER_ID (the routine ID, trig_...): ' >&2
  IFS= read -r TRIGGER || die "no value given"
  TRIGGER=${TRIGGER//[[:space:]]/}
  [[ $TRIGGER =~ ^trig_[A-Za-z0-9]{1,64}$ ]] || die "a routine ID looks like trig_ followed by letters and digits"
  HAVE_TRIGGER=1
}

get_denylist() {
  [ "$HAVE_DENYLIST" = 1 ] && return 0
  if [ -z "$DENYLIST" ]; then
    printf 'The privacy denylist is a text file with one regular expression per line (your real name, emails, hosts and private ids; never your GitHub login or the public handle in OWNER_NAME), kept outside every repo; docs/skills.md, "The privacy check", has a sample.\nPath to your privacy denylist file: ' >&2
    IFS= read -r DENYLIST || die "no path given"
  fi
  DENYLIST=${DENYLIST/#\~/$HOME}
  [ -f "$DENYLIST" ] || die "the denylist path is not a file: write one regular expression per line to a file outside every repo (docs/skills.md, \"The privacy check\") and give its path"
  local dir; dir=$(cd "$(dirname "$DENYLIST")" && pwd)
  if git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    die "the denylist is inside a git work tree; keep it outside every repo"
  fi
  # Each pattern must compile, there must be at least one, and none may match
  # a public name the starter writes (public_names). Report line numbers and
  # key names only, never a pattern.
  local names; mapfile -t names < <(public_names)
  python3 -I - "$DENYLIST" "${names[@]}" <<'PY' || die "the denylist failed validation (see above)"
import re, sys
names = [a.split("\t", 1) for a in sys.argv[2:]]
bad, public, n, partial = [], [], 0, False
for i, l in enumerate(open(sys.argv[1], encoding="utf-8"), 1):
    l = l.strip()
    if not l or l.startswith("#"):
        continue
    n += 1
    try:
        rx = re.compile(l, re.I)
    except re.error:
        bad.append(i)
        continue
    hits = [(k, v, m) for k, v in names for m in [rx.search(v)] if m]
    if hits:
        public.append(f"{i} ({', '.join(sorted({k for k, _, _ in hits}))})")
        partial = partial or any(m.group(0) != v for _, v, m in hits)
if bad:
    print("denylist: line(s) " + ", ".join(map(str, bad)) + " are not valid regular expressions", file=sys.stderr)
if public:
    print("denylist: line(s) " + "; ".join(public) + " match a public name from fleet.env that the starter writes into dozens of files,"
          " so every privacy scan would fail on every pull request. List your real name, emails, hosts and private ids,"
          " never your GitHub login or the public handle in OWNER_NAME (docs/skills.md, \"The privacy check\")", file=sys.stderr)
    if partial:
        print("denylist: a line that matches only part of a name (a surname inside your login, say) is refused too. List the"
              " name whole, such as first[ ._-]?last, rather than one part; word boundaries (\\bpart\\b) help only where"
              " your login runs the parts together, since a - or _ in it is a boundary too", file=sys.stderr)
if bad or public:
    sys.exit(1)
if n == 0:
    print("denylist: no patterns (it wants one regular expression per line; docs/skills.md, \"The privacy check\"); every privacy scan would check nothing, and skills-evals' test job would fail closed", file=sys.stderr)
    sys.exit(1)
PY
  # The mode bits from stat(2), not `find -perm /077`: BSD find (macOS) has
  # no `/` form, so it erred, the error was discarded, and nothing warned.
  if python3 -I -c 'import os, sys; sys.exit(0 if os.stat(sys.argv[1]).st_mode & 0o077 else 1)' "$DENYLIST"; then
    warn "the denylist is readable by other users; consider chmod 600"
  fi
  HAVE_DENYLIST=1
}

# public_names: "<fleet.env key><TAB><value>" for each public name the
# starter writes into the adopter's files (copy-starter.sh, lib/substitute.py):
# each login as given and in substitute.py's three forms (lower case; upper
# case with - and . as _; lower case with them as _), so a pattern that turns
# case-insensitive matching off with (?-i:...) is caught too; OWNER's noreply
# address (<id>+<login>@users.noreply.github.com, the id read from GitHub as
# copy-starter.sh reads it); OWNER_NAME, APP_NAME_PREFIX and each App's
# <prefix>-<app> name. Defaults are applied by load_config.
public_names() {
  local key v e low up uid
  for key in OWNER OWNER_TWO REVIEWER; do
    v=CFG_$key; v=${!v}
    [ -n "$v" ] || continue
    low=${v,,} up=${v^^}
    printf '%s\t%s\n' "$key" "$v" "$key" "$low" "$key" "${up//[-.]/_}" "$key" "${low//[-.]/_}"
  done
  if gh_read "users/$CFG_OWNER" && uid=$(printf '%s' "$GH_OUT" | jq -r '.id // empty') && [[ $uid =~ ^[1-9][0-9]{0,11}$ ]]; then
    printf '%s\t%s\n' "OWNER (noreply address)" "$uid+$CFG_OWNER@users.noreply.github.com" "OWNER (noreply address)" "$uid+${CFG_OWNER,,}@users.noreply.github.com"
  else
    warn "could not read $CFG_OWNER's GitHub id (HTTP ${GH_HTTP:-unknown}), so the denylist was not checked against your noreply address"
  fi
  printf '%s\t%s\n' OWNER_NAME "$CFG_OWNER_NAME" APP_NAME_PREFIX "$CFG_APP_NAME_PREFIX"
  for e in "${APPS[@]}"; do printf 'APP_NAME_PREFIX\t%s-%s\n' "$CFG_APP_NAME_PREFIX" "${e%%|*}"; done
}

set_one() { # repo env kind name
  local repo=$1 env=$2 kind=$3 name=$4 at
  if [ "$env" = - ]; then at=""; else at=" environment $env"; fi
  if [ "$env" != - ] && ! env_available "$repo"; then
    log "skip: $O/$repo$at $name: $repo is private and PLAN=free, so it has no environments"
    return 0
  fi
  if value_names "$kind" "$O/$repo" "$env"; then
    if grep -qxF -- "$name" <<<"$NAMES_OUT" && [ "$ROTATE" = 0 ]; then
      skip "$O/$repo$at has $kind $name"; return 0
    fi
  elif [ "$DRY_RUN" = 0 ]; then
    die "could not list the ${kind}s of $O/$repo$at (HTTP $GH_HTTP): run create-repos.sh$([ "$env" = - ] || echo " and create-environments.sh") first"
  fi
  if [ "$DRY_RUN" = 1 ]; then
    set_value "$kind" "$O/$repo" "$env" "$name" </dev/null
  else
    case $name in
      EVAL_ROUTINE_FIRE_BEARER) get_bearer; set_value "$kind" "$O/$repo" "$env" "$name" < <(printf '%s' "$BEARER") ;;
      ROUTINE_TRIGGER_ID) get_trigger; set_value "$kind" "$O/$repo" "$env" "$name" < <(printf '%s' "$TRIGGER") ;;
      PRIVACY_DENYLIST) get_denylist; set_value "$kind" "$O/$repo" "$env" "$name" < "$DENYLIST" ;;
      *) die "no source for $name" ;;
    esac
  fi
  did "set $kind $name in $O/$repo$at"
}

log "Owner $O, plan $CFG_PLAN$([ "$DRY_RUN" = 1 ] && echo ', DRY RUN')"
EVALS_STATE=""   # unknown until an evals-track entry asks
for entry in "${OTHER_VALUES[@]}"; do
  IFS='|' read -r repo env kind name _src <<<"$entry"
  [ -z "$ONLY" ] || [ "$ONLY" = "$(value_group "$name")" ] || continue
  if [ "$(repo_track "$repo")" = evals ]; then
    if [ -z "$EVALS_STATE" ]; then
      if evals_repo_exists; then EVALS_STATE=yes; else EVALS_STATE=no; fi
    fi
    if [ "$EVALS_STATE" = no ]; then
      log "skip: $O/$repo $kind $name: $repo does not exist yet (the evals track creates it; run this again then)"
      continue
    fi
  fi
  set_one "$repo" "$env" "$kind" "$name"
done
BEARER="" TRIGGER=""
finish
