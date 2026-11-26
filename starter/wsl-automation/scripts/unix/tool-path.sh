# shellcheck shell=bash
# Sourced by run-task.sh and install-schedule.sh, so the installer probes for
# tools exactly the way the runner will look for them at run time.

# PATH for a profile-less scheduler (cron's PATH is /usr/bin:/bin): ~/.local/bin,
# Homebrew's and the usual system directories are appended, and GNU coreutils'
# gnubin directories (Homebrew on macOS) go first.
unix_job_path() {
    local gnubin
    for gnubin in /usr/local/opt/coreutils/libexec/gnubin /opt/homebrew/opt/coreutils/libexec/gnubin; do
        if [[ -d $gnubin && :$PATH: != *":$gnubin:"* ]]; then PATH=$gnubin:$PATH; fi
    done
    PATH=$PATH:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
    export PATH
}

unix_find_flock() { command -v flock || true; }
unix_find_timeout() { command -v timeout || command -v gtimeout || true; }
