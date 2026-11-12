"""X10 and the kit's session miner, in the task installer.

Set-WslAutomationScheduledTasks.ps1 registered eight tasks (fourteen by the
time of re-pin round 9). With the restic
backup and the session keeper left out (DECISIONS X10), the backup task, the
keeper task and the keeper's two on-demand launchers go, with their
parameters, two of which (-BackupDir, -ResticRepoDir) were mandatory. The
Store-pwsh warning that sat in the keeper block stays: it protects the two
remaining pwsh-based S4U tasks too. The comment that explained the
indefinite-repetition trigger lived on the keeper trigger, so it moves to the
ccstatusline trigger, which now carries that construction first.

The source registers a daily session miner too, but the kit's own wrapper
(DECISIONS "Export record: wsl-automation") replaces the source's, so the
miner task keeps the kit's comment, time (07:17) and 30 minute limit. The task
health publish is left out with its script (DECISIONS "Re-pin (2026-11-03)"):
it reads the left-out restic repository and keeper log and feeds the source
account's fleet health audit. The weekly memory curation ships as the source
has it, the Docker watchdog ships (the Interactive task; the patch used to cut
it out together with the task health block, which left its parameters, tests
and summary line with nothing behind them), and so does the WSL memory log.

Re-pin round 9 (DECISIONS "Re-pin round 9"): the source gained the memory log
task (kept), a Claude settings sync task (left out, X9: it runs a skill of the
owner's registry), catch-up settings for the daily wsl.exe publish tasks (kept,
the session miner too, with the kit's 30 minute limit) and -EnableCodexTasks,
which the kit keeps for the Codex Cloud sync alone (the launcher is left out
with the keeper).

register-tasks.ps1, the thin elevated wrapper, follows the function's
parameters.

All text added here is ASCII (AGENTS.md: "Keep the PowerShell sources
ASCII-only"); the patch checks it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("kit_wsl_text", Path(__file__).with_name("_text.py"))
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

FUNC = "src/WslAutomation/Public/Set-WslAutomationScheduledTasks.ps1"
WRAPPER = "scripts/register-tasks.ps1"

HELP_HEAD = """    .SYNOPSIS
        Registers or updates the scheduled tasks that drive ccstatusline config sync, the WSL
        memory log, Codex Cloud environment sync, the daily usage census publish, the daily
        session miner, the weekly memory curation, the every-minute waiting feed publish, and the
        Docker Desktop WSL integration watchdog.

    .DESCRIPTION
        Creates eight Windows Scheduled Tasks, or updates them in place if they already exist: a
        ccstatusline config sync task that runs scripts/sync-ccstatusline-config.ps1 on a short
        repeating interval; a WSL memory log task that runs scripts/log-wsl-memory.ps1 on its own
        short repeating interval, appending one row of Windows and WSL memory statistics to a
        CSV; a Codex Cloud environment sync task that runs
        scripts/sync-codex-cloud-environments.ps1 at midnight and noon while the distro is running;
        a usage census publish task that runs scripts/publish-usage-census.sh inside the distro
        once a day, calling wsl.exe directly so no pwsh is involved; a session miner task that
        runs scripts/run-session-miner.sh inside the distro once a day, the same way; a memory
        curation task that runs scripts/run-memory-curation.sh the same way once a week; a
        waiting feed publish task that runs scripts/publish-waiting-feed.sh inside the distro every
        minute, the same way; and a Docker WSL integration watchdog task that runs
        scripts/ensure-docker-wsl-integration.ps1 (through conhost --headless) at logon and every
        30 minutes, restarting Docker Desktop when its WSL integration with the distro is broken.

        The watchdog is the one pwsh-based task that is Interactive, not S4U: 'docker desktop
        restart' relaunches the Docker Desktop GUI, which must land in the user's session rather
        than session 0, and the alert toast needs the user's desktop. conhost.exe --headless runs
        its pwsh without a console window, so the interactive run does not flash one.

        The other seven run as background S4U tasks (session 0), so they never flash a console
        window on the desktop. The three pwsh-based ones (ccstatusline sync, memory log, Codex
        Cloud sync) require an MSI PowerShell 7 and the "Log on as a batch job" right - see
        -PwshPath and scripts/grant-keeper-batch-logon.ps1. The usage census, session miner,
        memory curation and waiting feed tasks are S4U too, but their action is wsl.exe itself, so
        they need no pwsh at all.

        Every task's Settings and Principal are always (re)built fresh from this function's
        parameters, whether the task already exists or not, so their battery/idle behavior stays
        in sync. Re-running this function is idempotent for all eight tasks. The usage census and
        the session miner set StartWhenAvailable, with restarts: a day missed while the machine
        slept is caught up once it wakes, and a run that lands in WSL's post-wake transition
        window is retried (see AGENTS.md). The other tasks do not: a missed run stays missed
        rather than firing the instant the machine wakes, inside that window.

        The Codex Cloud environment sync task is disabled by default: it is registered or updated
        like the rest and then disabled. Pass -EnableCodexTasks to turn it on.

        Also archives any legacy scripts passed via -LegacyScriptsToArchive by renaming them
        out of the way, so a stale scheduled task still pointing at an old script path fails
        loudly instead of silently continuing to run superseded automation.

        Windows-only: throws immediately if $IsWindows is false.

    .PARAMETER ScriptsDir
        Directory containing sync-ccstatusline-config.ps1, log-wsl-memory.ps1,
        sync-codex-cloud-environments.ps1, ensure-docker-wsl-integration.ps1,
        publish-usage-census.sh, run-session-miner.sh, run-memory-curation.sh and
        publish-waiting-feed.sh.

    .PARAMETER DistroName
        Name of the WSL distro the tasks run in. Defaults to 'Ubuntu'.

    .PARAMETER CcstatuslineTaskName
"""

CENSUS_TIME_OLD = """        Time of day (HH:mm) the usage census task's daily trigger fires. Defaults to '12:37':
        the laptop is usually awake at midday, and :37 is well clear of the backup's :00 hourly
        retries.
"""
CENSUS_TIME_NEW = """        Time of day (HH:mm) the usage census task's daily trigger fires. Defaults to '12:37':
        the laptop is usually awake at midday, and :37 is off the hour, clear of other jobs that
        start on it.
"""

MINER_HELP_START = "    .PARAMETER SessionMinerTaskName\n"
MINER_HELP_END = "    .PARAMETER MemoryCurationTaskName\n"
MINER_PARAMS = """    .PARAMETER SessionMinerTaskName
        Name of the scheduled task that runs the session miner from WSL (skills-evals'
        scripts/run_session_miner.sh through scripts/run-session-miner.sh). Defaults to
        'Session Miner'.

    .PARAMETER SessionMinerTime
        Time of day (HH:mm) the session miner task's daily trigger fires. Defaults to '07:17':
        off the hour, and hours away from the usage census, which reads the same transcripts.

"""
MEMORY_TIME_OLD = "        to '13:47', an hour after the session miner so the two never overlap.\n"
MEMORY_TIME_NEW = "        to '13:47', clear of every other task's time.\n"
HEALTH_HELP_START = "    .PARAMETER TaskHealthTaskName\n"
HEALTH_HELP_END = "    .PARAMETER DockerWatchdogTaskName\n"
CLAUDE_SYNC_HELP_START = "    .PARAMETER ClaudeSettingsSyncTaskName\n"
CLAUDE_SYNC_HELP_END = "    .PARAMETER CodexCloudEnvironmentSyncTaskName\n"
CODEX_ENABLE_HELP_START = "    .PARAMETER EnableCodexTasks\n"
CODEX_ENABLE_HELP_END = "    .PARAMETER UsageCensusTaskName\n"
CODEX_ENABLE_HELP_NEW = """    .PARAMETER EnableCodexTasks
        Enables the Codex Cloud environment sync task. Off by default: it is still registered or
        updated, but then disabled. With this switch it is explicitly enabled (so it turns an
        already-disabled task back on). Re-running without it disables the task again.

"""

WSLEXE_OLD = """        Path to wsl.exe used as the usage census, session miner, memory curation, waiting feed and task health tasks' action. Defaults to
        %SystemRoot%\\System32\\wsl.exe.
"""
WSLEXE_NEW = """        Path to wsl.exe used as the usage census, session miner, memory curation and waiting
        feed tasks' action. Defaults to %SystemRoot%\\System32\\wsl.exe.
"""

PWSH_OLD = """        MSI install of PowerShell 7 (C:\\Program Files\\PowerShell\\7) when present - required for
        the S4U keeper and ccstatusline tasks, which run in session 0 where a Store-packaged pwsh
        cannot launch - then the per-user WindowsApps alias, then the pwsh.exe found on PATH. A
        warning is emitted if a Store-packaged path would be used for the keeper.

    .PARAMETER WtPath
        Path to wt.exe (Windows Terminal) used as both launcher tasks' action. Defaults to the
        stable per-user WindowsApps execution alias when present, else wt.exe on PATH.
"""
PWSH_NEW = """        MSI install of PowerShell 7 (C:\\Program Files\\PowerShell\\7) when present - required for
        the S4U ccstatusline, memory log and Codex Cloud tasks, which run in session 0 where a
        Store-packaged pwsh cannot launch - then the per-user WindowsApps alias, then the pwsh.exe
        found on PATH. A warning is emitted if a Store-packaged path would be used.
"""

EXAMPLES_OLD_START = "    .EXAMPLE\n        Set-WslAutomationScheduledTasks -ScriptsDir 'C:\\Users\\<you>\\repos\\wsl-automation\\scripts' -BackupDir"
EXAMPLES_END = "    #>\n"
EXAMPLES_NEW = """    .EXAMPLE
        Set-WslAutomationScheduledTasks -ScriptsDir 'C:\\Users\\<you>\\repos\\wsl-automation\\scripts'

        Registers (or updates) all eight scheduled tasks using default names, times and intervals.
        The Codex Cloud environment sync is left disabled without -EnableCodexTasks.

    .EXAMPLE
        Set-WslAutomationScheduledTasks -ScriptsDir $PSScriptRoot -WhatIf

        Shows what would change without actually registering, updating, or renaming anything.
"""

PARAMS_START = "        [Parameter(Mandatory)]\n        [string]$ScriptsDir,\n"
PARAMS_END = "        [string]$CcstatuslineTaskName = 'ccstatusline Config Sync',\n"
PARAMS_NEW = """        [Parameter(Mandatory)]
        [string]$ScriptsDir,

        [string]$DistroName = 'Ubuntu',

"""

CLAUDE_SYNC_PARAMS = (
    "        [string]$ClaudeSettingsSyncTaskName = 'Claude Settings Sync',\n\n"
    "        [int]$ClaudeSettingsSyncIntervalMinutes = 15,\n\n"
    "        [switch]$ClaudeSettingsSyncLive,\n\n"
)

MINER_DEFAULT_OLD = "        [string]$SessionMinerTime = '12:47',\n"
MINER_DEFAULT_NEW = "        [string]$SessionMinerTime = '07:17',\n"
HEALTH_DEFAULTS = "        [string]$TaskHealthTaskName = 'Task Health Publish',\n\n        [string]$TaskHealthTime = '23:47',\n\n"

WT_PARAM = "        [string]$WtPath = (Get-WslAutomationDefaultWtPath),\n\n"

TRIM_OLD = """    # A trailing separator is a common way to type or tab-complete a directory (for example
    # 'D:\\WSLBackups\\'). Embedded raw into a double-quoted native command-line argument, a
    # trailing backslash escapes the closing quote instead of terminating the value, corrupting
    # every argument after it - including silently dropping -NoPause, which reintroduces the
    # Read-Host hang under the hidden scheduled task that -NoPause exists to prevent. Trim
    # defensively for every user-supplied path embedded in a quoted argument string below.
    $BackupDir = $BackupDir.TrimEnd('\\')
    $ResticRepoDir = $ResticRepoDir.TrimEnd('\\')
"""
TRIM_NEW = """    # A trailing separator is a common way to type or tab-complete a directory (for example
    # 'C:\\Users\\<you>\\repos\\wsl-automation\\scripts\\'). Embedded raw into a double-quoted native
    # command-line argument, a trailing backslash escapes the closing quote instead of terminating
    # the value, corrupting every argument after it - for the wsl.exe tasks, --exec and the script
    # it runs. Trim defensively for every user-supplied path embedded in a quoted argument string
    # below.
"""

REMOVED_START = "    # --- Backup task: action + daily trigger repeating over the following day ---------------\n"
REMOVED_END = "    # --- ccstatusline task: background config sync -------------------------\n"
STORE_WARNING = """    # A Store-packaged pwsh (per-user WindowsApps alias or version-pinned WindowsApps package
    # path) cannot be activated in the session 0 the S4U pwsh tasks (ccstatusline sync, WSL
    # memory log, Codex Cloud sync) run in - the task fails with access denied every interval, silently. Warn
    # loudly so the operator installs PowerShell 7 via MSI (see the README and
    # scripts/grant-keeper-batch-logon.ps1) instead.
    $windowsAppsRoots = @(
        (Join-Path $env:LOCALAPPDATA 'Microsoft\\WindowsApps'),
        (Join-Path $env:ProgramFiles 'WindowsApps')
    )
    foreach ($windowsAppsRoot in $windowsAppsRoots) {
        if ($PwshPath -and $PwshPath.StartsWith($windowsAppsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            Write-Warning ("Scheduled task pwsh '$PwshPath' is a Store-packaged path; a Store pwsh cannot launch in the " +
                'non-interactive session 0 the S4U tasks use, so they would fail every interval. Install ' +
                'PowerShell 7 via MSI (C:\\Program Files\\PowerShell\\7) and re-run, or pass -PwshPath to a non-Store pwsh.')
            break
        }
    }

"""

CC_COMMENT_OLD = """    # Purely background work (reads the ccstatusline config out of WSL) that never needs a window,
    # so - like the keeper - it runs as an S4U/session-0 task. Otherwise it would flash its own
    # pwsh console every interval, the very flash the keeper split removed. -WindowStyle Hidden is
    # dropped for the same reason it was dropped from the keeper (it only shrinks, not removes, the
    # flash). Same session-0 requirements apply as the keeper: an MSI pwsh (see the warning above)
    # and the batch-logon right.
"""
CC_COMMENT_NEW = """    # Purely background work (reads the ccstatusline config out of WSL) that never needs a window,
    # so it runs as an S4U/session-0 task. Otherwise it would flash its own pwsh console every
    # interval. -WindowStyle Hidden is not used: Task Scheduler still creates the pwsh console
    # window before pwsh can hide it, so it only shrinks the flash; S4U ("run whether the user is
    # logged on or not", no stored password) runs in session 0, which has no desktop to draw one
    # on. Session-0 requirements: an MSI pwsh (see the warning above) and the batch-logon right.
"""

CC_TRIGGER_OLD = """    # Same indefinite-repetition construction as the keeper trigger above (-Once + creation-time
    # -RepetitionInterval, never mutated afterward); see the comment on $keeperTrigger for why.
"""
CC_TRIGGER_NEW = """    # -RepetitionInterval at creation time is the construction pwsh 7.6's ScheduledTasks module
    # actually supports for an indefinitely-repeating trigger: a -Once trigger built without it
    # has Repetition = $null (mutating .Repetition.Interval on it afterward throws "The property
    # 'Interval' cannot be found on this object"), and separately assigning Repetition.Duration =
    # '' is rejected by the Task Scheduler XML validator at registration time. Leaving
    # -RepetitionDuration unset here is required, not incidental - it is what makes the
    # repetition indefinite.
"""

CODEX_COMMENT_OLD = "    # This S4U task is background-only like the keeper and ccstatusline sync. It deliberately\n"
CODEX_COMMENT_NEW = "    # This S4U task is background-only like the ccstatusline sync. It deliberately\n"

WAITING_COMMENT_OLD = """    # minute with the indefinite-repetition construction the keeper trigger documents above
"""
WAITING_COMMENT_NEW = """    # minute with the indefinite-repetition construction the ccstatusline trigger documents above
"""

ARCHIVE_ANCHOR = "    # --- Archive legacy scripts this module supersedes ----------------------\n"
MINER_BLOCK_START = "    # --- Session miner: one daily trigger, wsl.exe as the action ------------\n"
MINER_BLOCK_END = "    # --- Memory curation: one weekly (Monday) trigger, wsl.exe as the action\n"
HEALTH_BLOCK_START = "    # --- Task health publish: one daily trigger, wsl.exe as the action ------\n"
DOCKER_BLOCK_START = "    # --- Docker WSL integration watchdog: logon + every 30 minutes, conhost --headless ----------\n"
CLAUDE_SYNC_BLOCK_START = "    # --- Claude settings sync task: Windows <-> WSL settings.json ---------------\n"
CODEX_CLOUD_BLOCK_START = "    # --- Codex Cloud environment sync: exactly two daily triggers ---------\n"
DOCKER_TRIGGER_OLD = "    # Trigger 2: the same indefinite-repetition construction as the keeper trigger above (-Once +\n"
DOCKER_TRIGGER_NEW = "    # Trigger 2: the same indefinite-repetition construction as the ccstatusline trigger above (-Once +\n"
MEMORY_TRIGGER_OLD = "    # Same indefinite-repetition construction as the keeper and ccstatusline triggers above.\n"
MEMORY_TRIGGER_NEW = "    # Same indefinite-repetition construction as the ccstatusline trigger above.\n"

CATCHUP_OLD = """    # --- Catch-up settings shared by the three daily wsl.exe publish tasks ---
    # Usage census, session miner and task health run once a day; a laptop asleep at that minute
    # used to skip the day (Task Scheduler result 0x800710E0, 2147946720 - Session Miner went
    # two days without a real run). StartWhenAvailable now runs the missed task once the machine
    # wakes. The backup keeps it off because wsl --export dies inside WSL's post-wake transition
    # window; these scripts only need a working wsl.exe, so a catch-up that lands in that window
    # and fails is retried (3 times, 10 minutes apart - past the ~270 s window) instead.
"""
CATCHUP_NEW = """    # --- Catch-up settings shared by the daily wsl.exe publish tasks ---
    # Usage census and session miner run once a day; a laptop asleep at that minute used to
    # skip the day (Task Scheduler result 0x800710E0, 2147946720 - the source's Session Miner
    # went two days without a real run). StartWhenAvailable now runs the missed task once the
    # machine wakes. The pwsh tasks keep it off because they can die inside WSL's post-wake
    # transition window; these scripts only need a working wsl.exe, so a catch-up that lands in
    # that window and fails is retried (3 times, 10 minutes apart - past the ~270 s window)
    # instead.
"""
MINER_SETTINGS_OLD = "    $sessionMinerSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `\n        -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew\n"
CODEX_TASKS_START = "    # --- Codex tasks: disabled unless -EnableCodexTasks ----------------------\n"
CODEX_TASKS_END = "    # --- Archive legacy scripts this module supersedes ----------------------\n"
CODEX_TASKS_NEW = """    # --- Codex Cloud sync: disabled unless -EnableCodexTasks -----------------
    # It is registered or updated above exactly as always, so it exists and its definition stays
    # current, and only then switched. Enabling is explicit too, so passing -EnableCodexTasks
    # turns an already-disabled task back on. Re-running without the switch leaves it disabled.
    $codexTaskVerb = if ($EnableCodexTasks) { 'Enable' } else { 'Disable' }
    if ($PSCmdlet.ShouldProcess($CodexCloudEnvironmentSyncTaskName, "$codexTaskVerb scheduled task")) {
        Set-WslScheduledTaskEnabled -TaskName $CodexCloudEnvironmentSyncTaskName -Enabled ([bool]$EnableCodexTasks)
    }

"""
CLAUDE_SUMMARY = (
    "    $claudeSettingsSyncMode = if ($ClaudeSettingsSyncLive) { 'live' } else { 'dry run' }\n"
    "    Write-Information -MessageData \"Claude settings sync task '$ClaudeSettingsSyncTaskName' (background/S4U, $claudeSettingsSyncMode): $claudeSettingsSyncArguments (repeats every $ClaudeSettingsSyncIntervalMinutes min, indefinitely)\" -InformationAction Continue\n"
)
CODEX_STATE_LINE = "    $codexTaskState = if ($EnableCodexTasks) { 'enabled' } else { 'disabled; pass -EnableCodexTasks to enable' }\n"
MINER_BLOCK = """    # --- Session miner: one daily trigger, wsl.exe as the action ------------
    # Same shape as the usage census (wsl.exe directly, S4U, session 0, the shared catch-up
    # settings with a longer limit: a missed day is caught up on wake, and the next run reads
    # every session since the last one either way). The wrapper clones skills-evals main and runs that copy's
    # scripts/run_session_miner.sh, which reads this machine's Claude Code transcripts and pushes
    # lesson records to the private registry's persistent/lessons branch. It refuses a scheduled
    # run until a --dry-run has been made by hand (see README.md), so registering the task before
    # setup is safe. A 30 minute limit (the shared settings' 15 minutes, raised) covers a first run,
    # which reads every session on the machine; IgnoreNew keeps a slow run from doubling up.
    $sessionMinerArguments = "--distribution $DistroName --cd `"$ScriptsDir`" --exec /bin/bash ./run-session-miner.sh"
    $sessionMinerAction = New-ScheduledTaskAction -Execute $WslExePath -Argument $sessionMinerArguments
    $sessionMinerTrigger = New-ScheduledTaskTrigger -Daily -At $SessionMinerTime | ConvertTo-WslLocalTimeTrigger
    $sessionMinerSettingsParams = $catchUpSettingsParams.Clone()
    $sessionMinerSettingsParams['ExecutionTimeLimit'] = New-TimeSpan -Minutes 30
    $sessionMinerSettings = New-ScheduledTaskSettingsSet @sessionMinerSettingsParams
    $sessionMinerPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\\$env:USERNAME" -LogonType S4U

    $existingSessionMinerTask = Get-ScheduledTask -TaskName $SessionMinerTaskName -ErrorAction SilentlyContinue
    if ($existingSessionMinerTask) {
        if ($PSCmdlet.ShouldProcess($SessionMinerTaskName, 'Update scheduled task')) {
            Set-WslScheduledTask -TaskName $SessionMinerTaskName -Action $sessionMinerAction -Trigger $sessionMinerTrigger `
                -Settings $sessionMinerSettings -Principal $sessionMinerPrincipal
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess($SessionMinerTaskName, 'Register scheduled task')) {
            Register-WslScheduledTask -TaskName $SessionMinerTaskName -Action $sessionMinerAction -Trigger $sessionMinerTrigger `
                -Settings $sessionMinerSettings -Principal $sessionMinerPrincipal
        }
    }

"""

SUMMARY_OLD_START = "    Write-Information -MessageData \"Backup task '$BackupTaskName'"
SUMMARY_OLD_END = "    Write-Information -MessageData \"ccstatusline task '$CcstatuslineTaskName'"
HEALTH_SUMMARY = (
    "    Write-Information -MessageData \"Task health task '$TaskHealthTaskName' (background/S4U): "
    "$WslExePath $taskHealthArguments (daily at $TaskHealthTime)\" -InformationAction Continue\n"
)


def _function(text: str, where: str) -> str:
    text = T.replace_between(text, "    .SYNOPSIS\n", "    .PARAMETER CcstatuslineTaskName\n", HELP_HEAD, where, keep_end=False)
    text = T.sub_once(text, CENSUS_TIME_OLD, CENSUS_TIME_NEW, where)
    text = T.replace_between(text, MINER_HELP_START, MINER_HELP_END, MINER_PARAMS, where)
    text = T.sub_once(text, MEMORY_TIME_OLD, MEMORY_TIME_NEW, where)
    text = T.replace_between(text, HEALTH_HELP_START, HEALTH_HELP_END, "", where)
    text = T.replace_between(text, CLAUDE_SYNC_HELP_START, CLAUDE_SYNC_HELP_END, "", where)
    text = T.replace_between(text, CODEX_ENABLE_HELP_START, CODEX_ENABLE_HELP_END, CODEX_ENABLE_HELP_NEW, where)
    text = T.sub_once(text, "sessions waiting on the owner) from WSL", "sessions waiting on you) from WSL", where)
    text = T.sub_once(text, WSLEXE_OLD, WSLEXE_NEW, where)
    text = T.sub_once(text, PWSH_OLD, PWSH_NEW, where)
    text = T.replace_between(text, EXAMPLES_OLD_START, EXAMPLES_END, EXAMPLES_NEW, where)
    text = T.sub_once(text, "This function manages seven related scheduled tasks by design",
                      "This function manages eight related scheduled tasks by design", where)
    text = T.replace_between(text, PARAMS_START, PARAMS_END, PARAMS_NEW, where)
    text = T.sub_once(text, MINER_DEFAULT_OLD, MINER_DEFAULT_NEW, where)
    text = T.sub_once(text, HEALTH_DEFAULTS, "", where)
    text = T.sub_once(text, CLAUDE_SYNC_PARAMS, "", where)
    text = T.sub_once(text, WT_PARAM, "", where)
    text = T.sub_once(text, TRIM_OLD, TRIM_NEW, where)
    text = T.replace_between(text, REMOVED_START, REMOVED_END, STORE_WARNING, where)
    text = T.sub_once(text, CC_COMMENT_OLD, CC_COMMENT_NEW, where)
    text = T.sub_once(text, CC_TRIGGER_OLD, CC_TRIGGER_NEW, where)
    text = T.sub_once(text, MEMORY_TRIGGER_OLD, MEMORY_TRIGGER_NEW, where)
    text = T.sub_once(text, DOCKER_TRIGGER_OLD, DOCKER_TRIGGER_NEW, where)
    text = T.sub_once(text, CODEX_COMMENT_OLD, CODEX_COMMENT_NEW, where)
    text = T.sub_once(text, WAITING_COMMENT_OLD, WAITING_COMMENT_NEW, where)
    text = T.replace_between(text, MINER_BLOCK_START, MINER_BLOCK_END, MINER_BLOCK, where)
    text = T.replace_between(text, HEALTH_BLOCK_START, DOCKER_BLOCK_START, "", where)
    text = T.replace_between(text, CLAUDE_SYNC_BLOCK_START, CODEX_CLOUD_BLOCK_START, "", where)
    text = T.sub_once(text, CATCHUP_OLD, CATCHUP_NEW, where)
    text = T.replace_between(text, CODEX_TASKS_START, CODEX_TASKS_END, CODEX_TASKS_NEW, where)
    # The summary: the backup, keeper and launcher lines go; the shared $codexTaskState stays
    # (the Codex Cloud line reads it); the Codex launcher, Claude settings sync and task health
    # lines go.
    text = T.replace_between(text, SUMMARY_OLD_START, SUMMARY_OLD_END, CODEX_STATE_LINE, where)
    text = T.sub_once(text, CLAUDE_SUMMARY, "", where)
    text = T.sub_once(text, HEALTH_SUMMARY, "", where)
    for gone in ("BackupDir", "ResticRepoDir", "KeeperTaskName", "LauncherTaskName", "WtPath", "restic", "the keeper", "keeper task", "keeperTrigger",
                 "TaskHealth", "task-health", "task health", "keeper trigger", "Keeper", "NoCodexRemoteControl", "codexLauncher",
                 "ClaudeSettingsSync", "sync-claude-settings", "Claude settings", "Claude Settings"):
        if gone in text:
            raise T.PatchError(f"{where}: {gone!r} is still mentioned")
    return text


WRAPPER_HELP_START = ".SYNOPSIS\n"
WRAPPER_HELP_END = ".PARAMETER CcstatuslineTaskName\n"
WRAPPER_HELP_NEW = """.SYNOPSIS
    Wrapper script for Set-WslAutomationScheduledTasks; installs or updates the ccstatusline
    config sync, WSL memory log, Codex Cloud environment sync, usage census publish, session
    miner, memory curation and waiting feed publish scheduled tasks, and the Docker Desktop WSL
    integration watchdog.

.DESCRIPTION
    Thin wrapper that imports the WslAutomation module and calls
    Set-WslAutomationScheduledTasks with the given parameters. Must be run from an elevated
    (Administrator) PowerShell session. Supports -WhatIf, which is passed straight through to
    Set-WslAutomationScheduledTasks so nothing is actually registered, updated, or renamed
    during a dry run.

.PARAMETER ScriptsDir
    Directory containing sync-ccstatusline-config.ps1, log-wsl-memory.ps1,
    sync-codex-cloud-environments.ps1, ensure-docker-wsl-integration.ps1,
    publish-usage-census.sh, run-session-miner.sh, run-memory-curation.sh and
    publish-waiting-feed.sh. Defaults to the directory this script lives in.

.PARAMETER DistroName
    Name of the WSL distro the tasks run in. Defaults to 'Ubuntu'.

"""

WRAPPER_MINER_OLD = """.PARAMETER SessionMinerTime
    Time of day (HH:mm) the session miner task's daily trigger fires. Defaults to '12:47'.
"""
WRAPPER_MINER_NEW = """.PARAMETER SessionMinerTime
    Time of day (HH:mm) the session miner task's daily trigger fires. Defaults to '07:17'.
"""
WRAPPER_HEALTH_START = ".PARAMETER TaskHealthTaskName\n"
WRAPPER_HEALTH_END = ".PARAMETER DockerWatchdogTaskName\n"
WRAPPER_CLAUDE_HELP_START = ".PARAMETER ClaudeSettingsSyncTaskName\n"
WRAPPER_CLAUDE_HELP_END = ".PARAMETER CodexCloudEnvironmentSyncTaskName\n"
WRAPPER_CODEX_HELP_START = ".PARAMETER EnableCodexTasks\n"
WRAPPER_CODEX_HELP_END = ".PARAMETER UsageCensusTaskName\n"
WRAPPER_CODEX_HELP_NEW = """.PARAMETER EnableCodexTasks
    Enables the Codex Cloud environment sync task. Off by default: it is still registered or
    updated, then disabled. With this switch it is enabled (even if currently disabled).
    Re-running without it disables it again.

"""
WRAPPER_CLAUDE_PARAMS = (
    "    [string]$ClaudeSettingsSyncTaskName = 'Claude Settings Sync',\n\n"
    "    [int]$ClaudeSettingsSyncIntervalMinutes = 15,\n\n"
    "    [switch]$ClaudeSettingsSyncLive,\n\n"
)
WRAPPER_WAITING_PARAM = """.PARAMETER WslExePath
"""
WRAPPER_WAITING_PARAM_NEW = """.PARAMETER WaitingFeedTaskName
    Name of the scheduled task that publishes the waiting feed every minute. Defaults to
    'Claude Waiting Feed Publish'.

.PARAMETER WslExePath
"""

WRAPPER_WSLEXE_OLD = """    Path to wsl.exe used as the usage census, session miner, memory curation, and task health tasks' action. Defaults to
    %SystemRoot%\\System32\\wsl.exe.
"""
WRAPPER_WSLEXE_NEW = """    Path to wsl.exe used as the usage census, session miner, memory curation and waiting feed
    tasks' action. Defaults to %SystemRoot%\\System32\\wsl.exe.
"""

WRAPPER_PWSH_OLD = """    Path to pwsh.exe used as the action executable for all the tasks. Defaults to an MSI install
    of PowerShell 7 (C:\\Program Files\\PowerShell\\7\\pwsh.exe) when present - required for the S4U
    background backup, keeper and ccstatusline tasks, which run in session 0 where a Store-packaged pwsh
    cannot launch - then the per-user WindowsApps alias, then the pwsh.exe found on PATH.
"""
WRAPPER_PWSH_NEW = """    Path to pwsh.exe used as the action executable for the pwsh-based tasks. Defaults to an MSI
    install of PowerShell 7 (C:\\Program Files\\PowerShell\\7\\pwsh.exe) when present - required for
    the S4U background ccstatusline, memory log and Codex Cloud tasks, which run in session 0
    where a Store-packaged pwsh cannot launch - then the per-user WindowsApps alias, then the
    pwsh.exe found on PATH.
"""

WRAPPER_EXAMPLES_START = ".EXAMPLE\n    ./register-tasks.ps1 -BackupDir 'C:\\Users"
WRAPPER_EXAMPLES_END = "#>\n"
WRAPPER_EXAMPLES_NEW = """.EXAMPLE
    ./register-tasks.ps1

    Registers (or updates) all the scheduled tasks from an elevated prompt, using default names,
    times, and intervals. The Codex Cloud environment sync is left disabled; add
    -EnableCodexTasks to enable it.

.EXAMPLE
    ./register-tasks.ps1 -WhatIf

    Shows what would change without actually registering, updating, or renaming anything.
"""

WRAPPER_PARAMS_START = "    [Parameter(Mandatory)]\n    [string]$BackupDir,\n"
WRAPPER_PARAMS_END = "    [string]$CcstatuslineTaskName = 'ccstatusline Config Sync',\n"
WRAPPER_PARAMS_NEW = "    [string]$DistroName = 'Ubuntu',\n\n"

WRAPPER_DEFAULTS_OLD = """    [string]$SessionMinerTime = '12:47',
"""
WRAPPER_DEFAULTS_NEW = """    [string]$SessionMinerTime = '07:17',
"""
WRAPPER_HEALTH_DEFAULTS_OLD = """    [string]$TaskHealthTaskName = 'Task Health Publish',

    [string]$TaskHealthTime = '23:47',

"""
WRAPPER_HEALTH_DEFAULTS_NEW = """    [string]$WaitingFeedTaskName = 'Claude Waiting Feed Publish',

"""

WRAPPER_PWSH_COMMENT_OLD = """    # is both stable across updates and launchable from the non-interactive session 0 the S4U
    # keeper task runs in; a Store pwsh"""
WRAPPER_PWSH_COMMENT_NEW = """    # is both stable across updates and launchable from the non-interactive session 0 the S4U
    # tasks run in; a Store pwsh"""

WRAPPER_CALL_START = "    Set-WslAutomationScheduledTasks -ScriptsDir $ScriptsDir -BackupDir"
WRAPPER_CALL_END = "\n    exit 0\n"
WRAPPER_CALL_NEW = """    Set-WslAutomationScheduledTasks -ScriptsDir $ScriptsDir -DistroName $DistroName `
        -CcstatuslineTaskName $CcstatuslineTaskName -CcstatuslineIntervalMinutes $CcstatuslineIntervalMinutes `
        -PwshPath $PwshPath -MemoryLogTaskName $MemoryLogTaskName `
        -MemoryLogIntervalMinutes $MemoryLogIntervalMinutes -MemoryLogDir $MemoryLogDir `
        -CodexCloudEnvironmentSyncTaskName $CodexCloudEnvironmentSyncTaskName -EnableCodexTasks:$EnableCodexTasks `
        -UsageCensusTaskName $UsageCensusTaskName -UsageCensusTime $UsageCensusTime `
        -SessionMinerTaskName $SessionMinerTaskName -SessionMinerTime $SessionMinerTime `
        -MemoryCurationTaskName $MemoryCurationTaskName -MemoryCurationTime $MemoryCurationTime `
        -WaitingFeedTaskName $WaitingFeedTaskName `
        -DockerWatchdogTaskName $DockerWatchdogTaskName -DockerWatchdogIntervalMinutes $DockerWatchdogIntervalMinutes `
        -DockerWatchdogLogonDelayMinutes $DockerWatchdogLogonDelayMinutes -WslExePath $WslExePath -ConhostPath $ConhostPath `
        -LegacyScriptsToArchive $LegacyScriptsToArchive -SkipTaskHistory:$SkipTaskHistory -WhatIf:$WhatIfPreference
"""


def _wrapper(text: str, where: str) -> str:
    text = T.replace_between(text, WRAPPER_HELP_START, WRAPPER_HELP_END, WRAPPER_HELP_NEW, where)
    text = T.sub_once(text, WRAPPER_MINER_OLD, WRAPPER_MINER_NEW, where)
    text = T.replace_between(text, WRAPPER_HEALTH_START, WRAPPER_HEALTH_END, "", where)
    text = T.replace_between(text, WRAPPER_CLAUDE_HELP_START, WRAPPER_CLAUDE_HELP_END, "", where)
    text = T.replace_between(text, WRAPPER_CODEX_HELP_START, WRAPPER_CODEX_HELP_END, WRAPPER_CODEX_HELP_NEW, where)
    text = T.sub_once(text, WRAPPER_WAITING_PARAM, WRAPPER_WAITING_PARAM_NEW, where)
    text = T.sub_once(text, WRAPPER_WSLEXE_OLD, WRAPPER_WSLEXE_NEW, where)
    text = T.sub_once(text, WRAPPER_PWSH_OLD, WRAPPER_PWSH_NEW, where)
    text = T.replace_between(text, WRAPPER_EXAMPLES_START, WRAPPER_EXAMPLES_END, WRAPPER_EXAMPLES_NEW, where)
    # The DistroName parameter moves up beside ScriptsDir, ahead of the removed block.
    text = T.sub_once(text, "    [string]$DistroName = 'Ubuntu',\n\n", "", where)
    text = T.replace_between(text, WRAPPER_PARAMS_START, WRAPPER_PARAMS_END, WRAPPER_PARAMS_NEW, where)
    text = T.sub_once(text, WRAPPER_DEFAULTS_OLD, WRAPPER_DEFAULTS_NEW, where)
    text = T.sub_once(text, WRAPPER_HEALTH_DEFAULTS_OLD, WRAPPER_HEALTH_DEFAULTS_NEW, where)
    text = T.sub_once(text, WRAPPER_CLAUDE_PARAMS, "", where)
    text = T.sub_once(text, WRAPPER_PWSH_COMMENT_OLD, WRAPPER_PWSH_COMMENT_NEW, where)
    text = T.replace_between(text, WRAPPER_CALL_START, WRAPPER_CALL_END, WRAPPER_CALL_NEW, where)
    for gone in ("BackupDir", "ResticRepoDir", "KeeperTaskName", "restic", "the keeper", "keeper task",
                 "TaskHealth", "task-health", "task health", "NoCodexRemoteControl", "Keeper",
                 "ClaudeSettingsSync", "sync-claude-settings", "Claude settings", "Claude Settings"):
        if gone in text:
            raise T.PatchError(f"{where}: {gone!r} is still mentioned")
    return text


def apply(root: Path, ctx) -> None:
    T.edit_file(root, FUNC, _function)
    T.edit_file(root, WRAPPER, _wrapper)
    T.check_ascii(root, FUNC)
    T.check_ascii(root, WRAPPER)
