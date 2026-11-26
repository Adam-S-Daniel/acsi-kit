#!/usr/bin/env bash
# run-all-tests.sh: run every export's own test suite and print one PASS/FAIL
# line per tree and form, then the totals. Exits 1 if any run failed. Each run
# goes through ../export/run_suites.py, which copies the tree to a temporary
# directory and runs the source repo's own setup and test command (its
# manifest's suite: block) in a PID namespace. A suite that installs Python
# packages gets its own virtual environment, so the trees' pins never meet in
# one interpreter. Failures listed in known-failures.txt, by exact id, are
# excused only when they account for the whole failure; anything else fails the
# run. A failing run's log is shown.
#
# The five base trees run in three forms (run_suites.py --owners): `invented`,
# the tree as exported; `one`, a one-account adopter's names (the second owner
# equal to the first); and `two`, two accounts whose names sort the other way
# round, with the example repos dropped, as an adopter does. skills-evals, the
# evals track's and the longest, runs in the invented form only. At most
# RUN_ALL_JOBS runs (default 6) are in flight at once. RUN_ALL_FORMS limits the
# forms to the ones it names, separated by spaces (the kit's CI runs one form
# per job, side by side).
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1   # no __pycache__ in a tree that copy-starter.sh may copy
cd "$(dirname "${BASH_SOURCE[0]}")"

base_trees=(agent-guidance repo-settings agent-skills agent-skills-private wsl-automation)
all_forms=(invented one two)
read -r -a forms <<<"${RUN_ALL_FORMS:-${all_forms[*]}}"
[ "${#forms[@]}" -gt 0 ] || { echo "RUN_ALL_FORMS names no form" >&2; exit 2; }
for f in "${forms[@]}"; do
  case " ${all_forms[*]} " in *" $f "*) ;; *) echo "RUN_ALL_FORMS: unknown form '$f' (want: ${all_forms[*]})" >&2; exit 2 ;; esac
done
with_evals=0
case " ${forms[*]} " in *" invented "*) with_evals=1 ;; esac
# "<tree> <form>", the slowest first so the last runs to start are the short ones.
runs=()
for f in "${forms[@]}"; do runs+=("agent-guidance $f"); done
for f in "${forms[@]}"; do runs+=("agent-skills $f"); done
[ "$with_evals" = 0 ] || runs+=("skills-evals invented")
for t in repo-settings agent-skills-private wsl-automation; do
  for f in "${forms[@]}"; do runs+=("$t $f"); done
done

logs=$(mktemp -d)
trap 'rm -rf "$logs"' EXIT
jobs_max=${RUN_ALL_JOBS:-6}
[[ "$jobs_max" =~ ^[1-9][0-9]*$ ]] || { echo "RUN_ALL_JOBS must be a positive integer" >&2; exit 2; }
label_of() { if [ "$2" = invented ]; then echo "$1"; else echo "$1 ($2)"; fi; }

passed=0 failed=0
# Start the runs, a bounded number at a time, then report in a fixed order.
# Each runs in its own temporary copy and PID namespace, and one that installs
# packages in its own virtual environment, so they share no state.
running=0
for run in "${runs[@]}"; do
  read -r t f <<<"$run"
  key="$t.$f"
  if ! grep -qxE "kit_name: $t" ../export/manifests/*.yml 2>/dev/null; then
    echo 2 > "$logs/$key.rc"; echo "no manifest names it" > "$logs/$key.log"; continue
  fi
  while [ "$running" -ge "$jobs_max" ]; do wait -n || true; running=$((running - 1)); done
  ( python3 ../export/run_suites.py --kit-name "$t" --owners "$f" --known-failures known-failures.txt > "$logs/$key.log" 2>&1
    echo $? > "$logs/$key.rc" ) &
  running=$((running + 1))
done
wait

report() { # tree form
  local t=$1 f=$2 key="$1.$2" label rc
  label=$(label_of "$t" "$f")
  rc=$(cat "$logs/$key.rc" 2>/dev/null || echo 1)
  if [ "$rc" = 0 ]; then
    passed=$((passed + 1)); sed -n "/^PASS /p; /^    known failure/p; /^    listed as known/p" "$logs/$key.log"
  else
    failed=$((failed + 1)); echo "FAIL $label (exit $rc):"; sed 's/^/    /' "$logs/$key.log"
  fi
}
# Every planned run is reported, tree by tree: one that left no exit code (it
# was killed, or never started) counts as failed.
declare -A planned=()
for run in "${runs[@]}"; do planned["${run/ /.}"]=1; done
total=0
for t in "${base_trees[@]}" skills-evals; do
  for f in "${forms[@]}"; do
    [ -n "${planned[$t.$f]:-}" ] || continue
    total=$((total + 1)); report "$t" "$f"
  done
done
echo "runs: $passed passed, $failed failed, $total total (${#base_trees[@]} base trees in the form(s) ${forms[*]}$([ "$with_evals" = 0 ] || echo ', skills-evals in the invented form'))"
[ "$failed" = 0 ]
