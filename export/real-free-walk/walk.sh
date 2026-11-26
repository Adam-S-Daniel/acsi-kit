#!/usr/bin/env bash
# walk.sh [--auth] <command...>: run one command as the Free test account, in
# an isolated HOME, for a real walk of the kit (export/real-free-walk/README.md).
#
# Reads its settings from the file REAL_WALK_ENV names (walk.env.example shows
# the keys). The file lives outside the kit and outside any repo: it names the
# test account. It is parsed, never sourced, and holds no secret.
#
# Every command runs with HOME, GH_CONFIG_DIR, GIT_CONFIG_GLOBAL and XDG_* under
# WALK_DIR/home, GH_TOKEN and GITHUB_TOKEN unset, and the commit identity set to
# the test account's noreply address. It refuses (exit 3) unless
# `gh api user` answers TEST_LOGIN, so nothing runs as the maintainer's own gh
# login. --auth skips that check, for `gh auth login` and `gh auth setup-git`
# only. A bad settings file exits 2.
set -euo pipefail

die() { echo "walk.sh: $*" >&2; exit 2; }

env_file=${REAL_WALK_ENV:-}
[ -n "$env_file" ] || die "set REAL_WALK_ENV to the path of your walk.env (see walk.env.example)"
[ -f "$env_file" ] || die "no such file: $env_file"

WALK_DIR="" TEST_LOGIN="" TEST_USER_ID=""
while IFS= read -r line || [ -n "$line" ]; do
  line=${line%$'\r'}
  case $line in ''|'#'*) continue ;; esac
  key=${line%%=*}
  [ "$key" != "$line" ] || die "$env_file: not KEY=value: $line"
  value=${line#*=}
  case $key in
    WALK_DIR) WALK_DIR=$value ;;
    TEST_LOGIN) TEST_LOGIN=$value ;;
    TEST_USER_ID) TEST_USER_ID=$value ;;
    *) die "$env_file: unknown key $key" ;;
  esac
done < "$env_file"

case $WALK_DIR in /*) ;; *) die "WALK_DIR must be an absolute path" ;; esac
[[ $TEST_LOGIN =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,37}[A-Za-z0-9])?$ ]] || die "TEST_LOGIN is not a GitHub login"
[[ $TEST_USER_ID =~ ^[1-9][0-9]*$ ]] || die "TEST_USER_ID must be the account's numeric id"
[ -d "$WALK_DIR/home" ] || die "no $WALK_DIR/home: create it first (README.md, Setup)"

export HOME="$WALK_DIR/home"
export GH_CONFIG_DIR="$HOME/.config/gh"
export GIT_CONFIG_GLOBAL="$HOME/.gitconfig"
export XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share"
export XDG_CACHE_HOME="$HOME/.cache" XDG_STATE_HOME="$HOME/.local/state"
unset GH_TOKEN GITHUB_TOKEN GH_ENTERPRISE_TOKEN GITHUB_ENTERPRISE_TOKEN
noreply="${TEST_USER_ID}+${TEST_LOGIN}@users.noreply.github.com"
export GIT_AUTHOR_NAME="$TEST_LOGIN" GIT_COMMITTER_NAME="$TEST_LOGIN"
export GIT_AUTHOR_EMAIL="$noreply" GIT_COMMITTER_EMAIL="$noreply"

[ $# -gt 0 ] || die "usage: walk.sh [--auth] <command...>"
if [ "$1" = "--auth" ]; then
  shift
  [ $# -gt 0 ] || die "usage: walk.sh --auth gh auth <login|setup-git|status|refresh> ..."
  exec "$@"
fi

who=$(gh api user --jq .login 2>/dev/null) || who=""
if [ "$who" != "$TEST_LOGIN" ]; then
  echo "walk.sh: refusing: gh is signed in as '${who:-nobody}', not $TEST_LOGIN" >&2
  exit 3
fi
exec "$@"
