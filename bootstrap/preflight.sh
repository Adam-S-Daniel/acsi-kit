#!/usr/bin/env bash
# preflight.sh [--config fleet.env] [--track base|evals|all]
#
# Read-only, and only about THIS machine: whether the tools the other scripts
# call are installed (and new enough; tar for the README's update block),
# whether gh is signed in as OWNER with the scopes a push of workflow files
# needs, whether git has a credential helper for https pushes (a FAIL without
# one; a WARN when it is not gh's, gh auth setup-git), and whether the kit
# sits where the scripts want it. It installs nothing, makes no write call to GitHub and
# writes nothing outside its own temp dir. Run it before step 2.
#
# Prints one line per check, PASS, FAIL, WARN or SKIP, and under every FAIL
# and WARN an indented "fix:" line with the command for your OS (macOS:
# brew; Linux: apt-get or dnf; anything else: the tool's install page).
# Then "N passed, N failed, N warnings, N skipped". Exit 0 when nothing
# failed (warnings are allowed), 1 otherwise. gh's own output is never
# printed, since it can show token fragments; only a login name and what a
# check concluded are. The bash 4.4+ check lives in lib/common.sh.
#
# --track is accepted like the other scripts' flag; no check here serves one
# track only (add-content.sh and regenerate.sh are base steps), so it changes
# nothing.
#
# Tests only: PREFLIGHT_OS=macos|debian|fedora|other overrides the detected
# OS, PREFLIGHT_WSL=1|0 the WSL detection. Tools are found through PATH only.
# Needs: bash 4.4+.

set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"

TRACK=all
parse_common_args "$@"
set -- "${REST_ARGS[@]}"
while [ $# -gt 0 ]; do
  case $1 in
    --track) [ $# -ge 2 ] || die "--track needs base, evals or all"; TRACK=$2; shift ;;
    --track=*) TRACK=${1#--track=} ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done
check_track "$TRACK"

PASS=0 FAIL=0 WARNS=0 SKIPPED=0
pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$*"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$*"; }
warn_() { WARNS=$((WARNS + 1)); printf 'WARN: %s\n' "$*"; }
skp()  { SKIPPED=$((SKIPPED + 1)); printf 'SKIP: %s\n' "$*"; }
fix()  { printf '      fix: %s\n' "$*"; }

# version_ge <have> <want>: dotted integers, 0 when have >= want. Anything
# after the first non-numeric part of have is ignored (2.54.0.windows.1 is
# 2.54.0), and a missing part counts as 0 (2.54 equals 2.54.0).
version_ge() {
  local IFS=. h w i hv wv n
  read -r -a h <<<"$1"
  read -r -a w <<<"$2"
  n=${#h[@]}; [ "${#w[@]}" -le "$n" ] || n=${#w[@]}
  for ((i = 0; i < n; i++)); do
    hv=${h[i]:-0} wv=${w[i]:-0}
    [[ $hv =~ ^[0-9]+$ ]] || { hv=0; n=$((i + 1)); }
    hv=$((10#$hv)) wv=$((10#$wv))
    [ "$hv" -le "$wv" ] || return 0
    [ "$hv" -ge "$wv" ] || return 1
  done
  return 0
}

# first_version <text>: the first dotted number in the text, or nothing.
first_version() {
  [[ $1 =~ ([0-9]+(\.[0-9]+)+) ]] && printf '%s' "${BASH_REMATCH[1]}"
  return 0
}

have() { command -v "$1" >/dev/null 2>&1; }

# ------------------------------------------------------------------ checks
check_missing() { # tool severity(fail|warn) why fix-command
  if [ "$2" = fail ]; then fail "$1 is not installed ($3)"; else warn_ "$1 is not installed ($3)"; fi
  fix "$4"
}

check_git() {
  local out v
  have git || { check_missing git fail "every script clones or pushes with it" "$(install_cmd git git git git https://git-scm.com/downloads)"; return 0; }
  out=$(git --version 2>/dev/null || true)
  v=$(first_version "$out")
  if [ -z "$v" ]; then
    warn_ "git is installed but its version could not be read"
  elif version_ge "$v" 2.54; then
    pass "git $v"
  else
    warn_ "git $v is older than 2.54, which config-based git hooks need on each durable machine (step 21); older git silently ignores them. Earlier steps do not need it"
    fix "$(install_cmd git git git git https://git-scm.com/downloads)"
    case $OS_KIND in debian) fix "the distribution's git can lag; for a newer one: sudo add-apt-repository ppa:git-core/ppa (Ubuntu), then sudo apt-get install -y git" ;; esac
  fi
}

# gh's token scopes, from the X-OAuth-Scopes header of `gh api -i user`. Sets
# SCOPES_SEEN (0 or 1) and SCOPES (comma separated). Nothing else of the
# response is kept or printed.
read_scopes() {
  local out line
  SCOPES_SEEN=0 SCOPES=""
  out=$("$GH" api -i user 2>/dev/null) || return 0
  while IFS= read -r line; do
    line=${line%$'\r'}
    [ -n "$line" ] || break
    if [[ ${line,,} =~ ^x-oauth-scopes:[[:space:]]*(.*)$ ]] && [ -n "${BASH_REMATCH[1]}" ]; then
      SCOPES_SEEN=1 SCOPES=${BASH_REMATCH[1]}
    fi
  done <<<"$out"
}
has_scope() { local s; for s in ${SCOPES//,/ }; do [ "$s" != "$1" ] || return 0; done; return 1; }

check_gh() {
  local out v login helpers
  if ! have "$GH"; then
    check_missing gh fail "every script reads or writes GitHub with it" "$(install_cmd gh gh gh gh https://cli.github.com)"
    return 0
  fi
  out=$("$GH" --version 2>/dev/null || true)
  v=$(first_version "$out")
  pass "gh ${v:-installed}"
  if ! "$GH" auth status >/dev/null 2>&1; then
    fail "gh is not signed in"
    fix "gh auth login"
    return 0
  fi
  login=$("$GH" api user --jq .login 2>/dev/null) || login=""
  if [ -z "$login" ]; then
    warn_ "gh is signed in, but the active account's login could not be read"
  elif [ "$CONFIG_STATE" = ok ]; then
    if [ "$CFG_OWNER_TYPE" = user ]; then
      if [ "${login,,}" = "${CFG_OWNER,,}" ]; then
        pass "gh is signed in as $login, the OWNER in $CONFIG"
      else
        fail "gh is signed in as $login, but OWNER in $CONFIG is $CFG_OWNER"
        fix "gh auth login   (as $CFG_OWNER; gh auth switch -u $CFG_OWNER if both accounts are signed in)"
      fi
    else
      warn_ "OWNER $CFG_OWNER is an organization: whether $login belongs to it and may administer it cannot be checked here (gh is signed in as $login)"
    fi
  else
    pass "gh is signed in as $login"
  fi
  read_scopes
  if [ "$SCOPES_SEEN" = 1 ]; then
    if has_scope workflow; then
      pass "gh's token has the workflow scope"
    else
      fail "gh's token lacks the workflow scope, so GitHub rejects a push that adds .github/workflows/ files (copy-starter.sh)"
      fix "gh auth refresh -h github.com -s workflow"
    fi
    if has_scope repo; then
      pass "gh's token has the repo scope"
    else
      fail "gh's token lacks the repo scope"
      fix "gh auth refresh -h github.com -s repo"
    fi
  else
    warn_ "gh's token scopes could not be read (a fine-grained or App token sends no scope header); it needs repository administration, contents, workflows, secrets, variables, environments and pull requests"
  fi
  if have git; then
    helpers=$({ git config --get-all credential.https://github.com.helper; git config --get-all credential.helper; } 2>/dev/null || true)
    if [[ $helpers == *"auth git-credential"* ]]; then
      pass "git pushes over https with gh's credential"
    elif [ -z "${helpers//[[:space:]]/}" ]; then
      # Every push needs a helper: the scripts push with GIT_TERMINAL_PROMPT=0,
      # so without one git cannot ask for a password and the push fails.
      fail "git has no credential helper for https pushes, which every script that pushes needs (copy-starter.sh from step 4, regenerate.sh)"
      fix "gh auth setup-git"
    else
      # Another helper (osxkeychain, Git Credential Manager) can push, but as
      # whatever account it holds, which may not be the one gh is signed in as.
      warn_ "git pushes with another credential helper, not gh's, so a push goes as whatever account that helper holds; gh's pushes as the account gh is signed in as (OWNER)"
      fix "gh auth setup-git"
    fi
  fi
}

# tar: the README's update block ("Update your copy of the kit") unpacks the
# newest bootstrap/ with it, and update-kit.sh needs it.
check_tar() {
  if have tar; then
    pass "tar is installed"
  else
    check_missing tar fail "the README's update block and update-kit.sh unpack the newest kit with it" "$(install_cmd tar "" tar tar https://www.gnu.org/software/tar/)"
  fi
}

check_jq() {
  local out v
  have jq || { check_missing jq fail "every script parses JSON with it" "$(install_cmd jq jq jq jq https://jqlang.github.io/jq/download/)"; return 0; }
  out=$(jq --version 2>/dev/null || true)
  v=$(first_version "$out")
  if [ -z "$v" ]; then
    warn_ "jq is installed but its version could not be read (verify.sh needs 1.6 or newer)"
  elif version_ge "$v" 1.6; then
    pass "jq $v"
  else
    fail "jq $v is older than 1.6, which verify.sh needs (@base64d)"
    fix "$(install_cmd jq jq jq jq https://jqlang.github.io/jq/download/)"
  fi
}

check_python() {
  local out v
  have python3 || { check_missing python3 fail "most scripts run python3" "$(install_cmd python3 python python3 python3 https://www.python.org/downloads/)"; return 0; }
  out=$(python3 -I -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null || true)
  v=$(first_version "$out")
  if [ -z "$v" ]; then
    fail "python3 is installed but does not run"
    fix "$(install_cmd python3 python python3 python3 https://www.python.org/downloads/)"
    return 0
  elif version_ge "$v" 3.9; then
    pass "python3 $v"
  else
    fail "python3 $v is older than 3.9"
    fix "$(install_cmd python3 python python3 python3 https://www.python.org/downloads/)"
  fi
  # The scripts run python3 -I, which implies -s: the per-user site directory
  # (pip install --user) is NOT on its path, so probe the same way, and never
  # advise --user.
  if python3 -I -c 'import yaml' >/dev/null 2>&1; then
    pass "python3 -I can import PyYAML"
  else
    fail "python3 -I cannot import PyYAML (the scripts run python3 isolated, which ignores pip install --user)"
    case $OS_KIND in
      debian) fix "sudo apt-get install -y python3-yaml" ;;
      fedora) fix "sudo dnf install -y python3-pyyaml" ;;
      macos)
        # Homebrew has no pyyaml formula (formulae.brew.sh, checked
        # 2026-11-25), and its python3 refuses a pip install outside a
        # virtual environment, so the venv is the one line that works.
        fix "a virtual environment that is active when you run the scripts: python3 -m venv ~/.venvs/kit && . ~/.venvs/kit/bin/activate && python3 -m pip install pyyaml"
        ;;
      *) fix "python3 -m pip install pyyaml   (into the interpreter's own site, such as an active virtual environment; not --user)" ;;
    esac
  fi
}

check_node() {
  local t
  for t in node npm; do
    if have "$t"; then
      pass "$t is installed"
    else
      check_missing "$t" fail "add-content.sh, step 1, builds the contributor rules with it" "$(node_install_cmd "$t")"
    fi
  done
}

check_claude() {
  if have claude; then
    pass "claude (Claude Code) is installed"
  else
    check_missing claude warn "the /adopt skill and step 21 need it; bootstrap/status.sh alone does not" "install Claude Code from https://docs.claude.com/en/docs/claude-code/setup"
  fi
}

check_actions_lock() {
  have "$GH" || { skp "gh actions-lock: gh is not installed"; return 0; }
  if "$GH" actions-lock --help >/dev/null 2>&1; then
    pass "the gh actions-lock extension is installed"
  else
    warn_ "the gh actions-lock extension is not installed (step 18, regenerate.sh actions-lock)"
    fix "gh extension install github/gh-actions-lock"
  fi
}

check_kit_location() {
  local top
  have git || { skp "kit location: git is not installed"; return 0; }
  top=$(git -C "$KIT" rev-parse --show-toplevel 2>/dev/null) || top=""
  if { [ -n "$top" ] && [ "$(cd "$top" && pwd -P)" != "$(cd "$KIT" && pwd -P)" ]; } \
      || git -C "$KIT/.." rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fail "this kit is inside another git repository ($KIT): that repository's CLAUDE.md and AGENTS.md would load into the session"
    fix "clone the kit outside every other repository and run it there"
  else
    pass "the kit is not inside another git repository"
  fi
}

check_config() {
  case $CONFIG_STATE in
    ok) pass "$CONFIG parses (OWNER $CFG_OWNER)"; check_time_zone ;;
    missing) skp "$CONFIG does not exist yet, so the account checks are skipped: do step 0 (cp bootstrap/fleet.env.example fleet.env, then fill it in)" ;;
    *) fail "$CONFIG does not parse: $CONFIG_ERR"; fix "edit $CONFIG; bootstrap/fleet.env.example shows each key" ;;
  esac
}

# A WARN, not a FAIL: only copy-starter.sh needs TIME_ZONE (step 6 onward), and
# a setup that copied the starter before the key existed must not fail here.
check_time_zone() {
  if [ -z "$CFG_TIME_ZONE" ]; then
    warn_ "$CONFIG has no TIME_ZONE; copy-starter.sh will refuse until it is set"
    fix "$_TIME_ZONE_HELP"
  elif [ "$(time_zone_state "$CFG_TIME_ZONE")" = nodb ]; then
    warn_ "TIME_ZONE $CFG_TIME_ZONE could not be checked: $_TIME_ZONE_NODB_HELP"
    fix "pip install tzdata (for the python3 that preflight.sh found), or your OS's tzdata package"
  else
    pass "TIME_ZONE $CFG_TIME_ZONE is a zone this machine knows"
  fi
}

check_wsl() {
  [ "$IS_WSL" = 1 ] || return 0
  if have pwsh.exe; then
    pass "WSL: pwsh.exe is reachable (step 22's scheduled tasks run in PowerShell 7 on the Windows side)"
  else
    warn_ "WSL: pwsh.exe is not reachable from here; step 22's scheduled tasks need PowerShell 7 on the Windows side (not needed before then)"
    fix "on Windows: winget install --id Microsoft.PowerShell"
  fi
}

# ------------------------------------------------------------------ run
detect_os
CONFIG_STATE=ok CONFIG_ERR=""
if [ ! -f "$CONFIG" ]; then
  CONFIG_STATE=missing
elif CONFIG_ERR=$( (load_config "$CONFIG") 2>&1 >/dev/null ); then
  load_config "$CONFIG"
else
  CONFIG_STATE=bad
  CONFIG_ERR=${CONFIG_ERR//$'\n'/; }
  CONFIG_ERR=${CONFIG_ERR#ERROR: }
fi

pass "bash ${BASH_VERSION%%[^0-9.]*} (4.4 or newer needed; lib/common.sh enforces it)"
check_git
check_gh
check_jq
check_tar
check_python
check_node
check_claude
check_actions_lock
check_kit_location
check_config
check_wsl

printf '%d passed, %d failed, %d warnings, %d skipped\n' "$PASS" "$FAIL" "$WARNS" "$SKIPPED"
[ "$FAIL" = 0 ]
