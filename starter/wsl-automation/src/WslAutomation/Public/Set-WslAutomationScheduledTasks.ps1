#requires -Version 7.6

function Set-WslAutomationScheduledTasks {
    <#
    .SYNOPSIS
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
        Name of the scheduled task that syncs the ccstatusline config from WSL. Defaults to
        'ccstatusline Config Sync'.

    .PARAMETER CcstatuslineIntervalMinutes
        How often, in minutes, the ccstatusline config sync task repeats indefinitely. Defaults
        to 5.

    .PARAMETER MemoryLogTaskName
        Name of the scheduled task that logs WSL and Windows memory statistics. Defaults to
        'WSL Memory Log'.

    .PARAMETER MemoryLogIntervalMinutes
        How often, in minutes, the memory log task repeats indefinitely. Defaults to 5.

    .PARAMETER MemoryLogDir
        Directory the memory log task writes samples.csv to. Defaults to
        %LOCALAPPDATA%\WslMemoryLog, resolved when the task is registered and passed to the task
        explicitly so it does not depend on the task's own environment.

    .PARAMETER CodexCloudEnvironmentSyncTaskName
        Name of the scheduled task that reconciles Codex Cloud environments. Defaults to
        'Codex Cloud Environment Sync'.

    .PARAMETER EnableCodexTasks
        Enables the Codex Cloud environment sync task. Off by default: it is still registered or
        updated, but then disabled. With this switch it is explicitly enabled (so it turns an
        already-disabled task back on). Re-running without it disables the task again.

    .PARAMETER UsageCensusTaskName
        Name of the scheduled task that publishes the daily usage census from WSL. Defaults to
        'Usage Census Publish'.

    .PARAMETER UsageCensusTime
        Time of day (HH:mm) the usage census task's daily trigger fires. Defaults to '12:37':
        the laptop is usually awake at midday, and :37 is off the hour, clear of other jobs that
        start on it.

    .PARAMETER SessionMinerTaskName
        Name of the scheduled task that runs the session miner from WSL (skills-evals'
        scripts/run_session_miner.sh through scripts/run-session-miner.sh). Defaults to
        'Session Miner'.

    .PARAMETER SessionMinerTime
        Time of day (HH:mm) the session miner task's daily trigger fires. Defaults to '07:17':
        off the hour, and hours away from the usage census, which reads the same transcripts.

    .PARAMETER MemoryCurationTaskName
        Name of the scheduled task that runs the weekly memory curation from WSL. Defaults to
        'Memory Curation'.

    .PARAMETER MemoryCurationTime
        Time of day (HH:mm) the memory curation task's weekly (Monday) trigger fires. Defaults
        to '13:47', clear of every other task's time.

    .PARAMETER WaitingFeedTaskName
        Name of the scheduled task that publishes the waiting feed (the Claude Code cloud
        sessions waiting on you) from WSL every minute. Defaults to
        'Claude Waiting Feed Publish'.

    .PARAMETER DockerWatchdogTaskName
        Name of the scheduled task that runs the Docker Desktop WSL integration watchdog.
        Defaults to 'Docker WSL Integration Watchdog'.

    .PARAMETER DockerWatchdogIntervalMinutes
        How often, in minutes, the watchdog task repeats indefinitely. Defaults to 30. The
        watchdog's own wake guard defers a repetition that lands right after a boot or resume.

    .PARAMETER DockerWatchdogLogonDelayMinutes
        Delay, in minutes, after logon before the watchdog's at-logon trigger fires. Defaults to
        12: WSL's post-boot init window runs to roughly 270 seconds, and Docker Desktop starts at
        login too, so the check waits beyond both (see AGENTS.md).

    .PARAMETER WslExePath
        Path to wsl.exe used as the usage census, session miner, memory curation and waiting
        feed tasks' action. Defaults to %SystemRoot%\System32\wsl.exe.

    .PARAMETER ConhostPath
        Path to conhost.exe used as the Docker watchdog task's action executable, with
        --headless so the interactive run shows no console window. Defaults to
        %SystemRoot%\System32\conhost.exe.

    .PARAMETER PwshPath
        Path to pwsh.exe used as the action executable for the pwsh-based tasks. Defaults to an
        MSI install of PowerShell 7 (C:\Program Files\PowerShell\7) when present - required for
        the S4U ccstatusline, memory log and Codex Cloud tasks, which run in session 0 where a
        Store-packaged pwsh cannot launch - then the per-user WindowsApps alias, then the pwsh.exe
        found on PATH. A warning is emitted if a Store-packaged path would be used.

    .PARAMETER LegacyScriptsToArchive
        Paths to legacy scripts that should be renamed out of the way because this module
        supersedes them. Workaround included for invocation via `pwsh -File ... -LegacyScriptsToArchive
        "C:\a.ps1","C:\b.ps1"` from another shell (notably Windows PowerShell 5.1): -File mode
        never re-parses commas, so the two paths can arrive flattened into one literal string
        "C:\a.ps1,C:\b.ps1". Any element that is a comma-joined list of rooted Windows paths
        (each looking like `C:\...` or `\\server\share\...`) is automatically expanded back into
        separate paths before archiving.

    .PARAMETER SkipTaskHistory
        Skips enabling the Microsoft-Windows-TaskScheduler/Operational event log (the "History"
        tab in Task Scheduler), which this function otherwise enables once per run if it is
        currently disabled. A failure to enable it only warns; it never aborts task
        registration. See README.md's "Task history" section for what the log records and how
        to read it.

    .EXAMPLE
        Set-WslAutomationScheduledTasks -ScriptsDir 'C:\Users\<you>\repos\wsl-automation\scripts'

        Registers (or updates) all eight scheduled tasks using default names, times and intervals.
        The Codex Cloud environment sync is left disabled without -EnableCodexTasks.

    .EXAMPLE
        Set-WslAutomationScheduledTasks -ScriptsDir $PSScriptRoot -WhatIf

        Shows what would change without actually registering, updating, or renaming anything.
    #>
    [System.Diagnostics.CodeAnalysis.SuppressMessage(
        'PSUseSingularNouns',
        '',
        Justification = 'This function manages eight related scheduled tasks by design; Set-WslAutomationScheduledTasks is the name specified by the project spec.')]
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)]
        [string]$ScriptsDir,

        [string]$DistroName = 'Ubuntu',

        [string]$CcstatuslineTaskName = 'ccstatusline Config Sync',

        [int]$CcstatuslineIntervalMinutes = 5,

        [string]$MemoryLogTaskName = 'WSL Memory Log',

        [int]$MemoryLogIntervalMinutes = 5,

        [string]$MemoryLogDir = (Join-Path $env:LOCALAPPDATA 'WslMemoryLog'),

        [string]$CodexCloudEnvironmentSyncTaskName = 'Codex Cloud Environment Sync',

        [switch]$EnableCodexTasks,

        [string]$UsageCensusTaskName = 'Usage Census Publish',

        [string]$UsageCensusTime = '12:37',

        [string]$SessionMinerTaskName = 'Session Miner',

        [string]$SessionMinerTime = '07:17',

        [string]$MemoryCurationTaskName = 'Memory Curation',

        [string]$MemoryCurationTime = '13:47',

        [string]$WaitingFeedTaskName = 'Claude Waiting Feed Publish',

        [string]$DockerWatchdogTaskName = 'Docker WSL Integration Watchdog',

        [int]$DockerWatchdogIntervalMinutes = 30,

        [int]$DockerWatchdogLogonDelayMinutes = 12,

        [string]$WslExePath = (Join-Path $env:SystemRoot 'System32\wsl.exe'),

        [string]$ConhostPath = (Join-Path $env:SystemRoot 'System32\conhost.exe'),

        [string]$PwshPath = (Get-WslAutomationDefaultPwshPath),

        [string[]]$LegacyScriptsToArchive = @(),

        [switch]$SkipTaskHistory
    )

    if (-not $IsWindows) {
        throw 'Set-WslAutomationScheduledTasks can only run on Windows.'
    }

    # A trailing separator is a common way to type or tab-complete a directory (for example
    # 'C:\Users\<you>\repos\wsl-automation\scripts\'). Embedded raw into a double-quoted native
    # command-line argument, a trailing backslash escapes the closing quote instead of terminating
    # the value, corrupting every argument after it - for the wsl.exe tasks, --exec and the script
    # it runs. Trim defensively for every user-supplied path embedded in a quoted argument string
    # below.
    $ScriptsDir = $ScriptsDir.TrimEnd('\')
    $MemoryLogDir = $MemoryLogDir.TrimEnd('\')
    $PwshPath = $PwshPath.TrimEnd('\')

    # A Store-packaged pwsh (per-user WindowsApps alias or version-pinned WindowsApps package
    # path) cannot be activated in the session 0 the S4U pwsh tasks (ccstatusline sync, WSL
    # memory log, Codex Cloud sync) run in - the task fails with access denied every interval, silently. Warn
    # loudly so the operator installs PowerShell 7 via MSI (see the README and
    # scripts/grant-keeper-batch-logon.ps1) instead.
    $windowsAppsRoots = @(
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'),
        (Join-Path $env:ProgramFiles 'WindowsApps')
    )
    foreach ($windowsAppsRoot in $windowsAppsRoots) {
        if ($PwshPath -and $PwshPath.StartsWith($windowsAppsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            Write-Warning ("Scheduled task pwsh '$PwshPath' is a Store-packaged path; a Store pwsh cannot launch in the " +
                'non-interactive session 0 the S4U tasks use, so they would fail every interval. Install ' +
                'PowerShell 7 via MSI (C:\Program Files\PowerShell\7) and re-run, or pass -PwshPath to a non-Store pwsh.')
            break
        }
    }

    # --- ccstatusline task: background config sync -------------------------
    # Purely background work (reads the ccstatusline config out of WSL) that never needs a window,
    # so it runs as an S4U/session-0 task. Otherwise it would flash its own pwsh console every
    # interval. -WindowStyle Hidden is not used: Task Scheduler still creates the pwsh console
    # window before pwsh can hide it, so it only shrinks the flash; S4U ("run whether the user is
    # logged on or not", no stored password) runs in session 0, which has no desktop to draw one
    # on. Session-0 requirements: an MSI pwsh (see the warning above) and the batch-logon right.
    $ccstatuslineScriptPath = Join-Path $ScriptsDir 'sync-ccstatusline-config.ps1'
    $ccstatuslineArguments = "-NoProfile -File `"$ccstatuslineScriptPath`" -DistroName $DistroName"
    $ccstatuslineAction = New-ScheduledTaskAction -Execute $PwshPath -Argument $ccstatuslineArguments

    # -RepetitionInterval at creation time is the construction pwsh 7.6's ScheduledTasks module
    # actually supports for an indefinitely-repeating trigger: a -Once trigger built without it
    # has Repetition = $null (mutating .Repetition.Interval on it afterward throws "The property
    # 'Interval' cannot be found on this object"), and separately assigning Repetition.Duration =
    # '' is rejected by the Task Scheduler XML validator at registration time. Leaving
    # -RepetitionDuration unset here is required, not incidental - it is what makes the
    # repetition indefinite.
    $ccstatuslineTrigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).Date) `
        -RepetitionInterval (New-TimeSpan -Minutes $CcstatuslineIntervalMinutes) | ConvertTo-WslLocalTimeTrigger

    # Settings/Principal are always rebuilt fresh for the ccstatusline task too, regardless of
    # whether it already exists, so its battery/idle behavior always matches this function's
    # defaults.
    $ccstatuslineSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew
    $ccstatuslinePrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U

    $existingCcstatuslineTask = Get-ScheduledTask -TaskName $CcstatuslineTaskName -ErrorAction SilentlyContinue
    if ($existingCcstatuslineTask) {
        if ($PSCmdlet.ShouldProcess($CcstatuslineTaskName, 'Update scheduled task')) {
            Set-WslScheduledTask -TaskName $CcstatuslineTaskName -Action $ccstatuslineAction -Trigger $ccstatuslineTrigger `
                -Settings $ccstatuslineSettings -Principal $ccstatuslinePrincipal
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess($CcstatuslineTaskName, 'Register scheduled task')) {
            Register-WslScheduledTask -TaskName $CcstatuslineTaskName -Action $ccstatuslineAction -Trigger $ccstatuslineTrigger `
                -Settings $ccstatuslineSettings -Principal $ccstatuslinePrincipal
        }
    }

    # --- WSL memory log task: periodic CSV sample ----------------------------
    # Background-only like the ccstatusline sync, so it is S4U/session 0 as well (no console
    # flash every interval) with the same MSI pwsh and batch-logon requirements. It reads WSL's
    # memory the way the ccstatusline sync reads its config, but only while the VM is already
    # running, so it never boots it. The log directory is resolved here, at install time, and
    # passed explicitly: an S4U task should not rely on the environment it runs in.
    $memoryLogScriptPath = Join-Path $ScriptsDir 'log-wsl-memory.ps1'
    $memoryLogArguments = "-NoProfile -File `"$memoryLogScriptPath`" -LogDir `"$MemoryLogDir`" -DistroName $DistroName"
    $memoryLogAction = New-ScheduledTaskAction -Execute $PwshPath -Argument $memoryLogArguments

    # Same indefinite-repetition construction as the ccstatusline trigger above.
    $memoryLogTrigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).Date) `
        -RepetitionInterval (New-TimeSpan -Minutes $MemoryLogIntervalMinutes) | ConvertTo-WslLocalTimeTrigger

    $memoryLogSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew
    $memoryLogPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U

    $existingMemoryLogTask = Get-ScheduledTask -TaskName $MemoryLogTaskName -ErrorAction SilentlyContinue
    if ($existingMemoryLogTask) {
        if ($PSCmdlet.ShouldProcess($MemoryLogTaskName, 'Update scheduled task')) {
            Set-WslScheduledTask -TaskName $MemoryLogTaskName -Action $memoryLogAction -Trigger $memoryLogTrigger `
                -Settings $memoryLogSettings -Principal $memoryLogPrincipal
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess($MemoryLogTaskName, 'Register scheduled task')) {
            Register-WslScheduledTask -TaskName $MemoryLogTaskName -Action $memoryLogAction -Trigger $memoryLogTrigger `
                -Settings $memoryLogSettings -Principal $memoryLogPrincipal
        }
    }

    # --- Codex Cloud environment sync: exactly two daily triggers ---------
    # This S4U task is background-only like the ccstatusline sync. It deliberately
    # has no StartWhenAvailable setting: it preserves the exact noon/midnight attempts and a
    # missed time stays missed. The wrapper checks state but never starts WSL.
    $codexCloudSyncScriptPath = Join-Path $ScriptsDir 'sync-codex-cloud-environments.ps1'
    $codexCloudSyncArguments = "-NoProfile -File `"$codexCloudSyncScriptPath`" -DistroName $DistroName"
    $codexCloudSyncAction = New-ScheduledTaskAction -Execute $PwshPath -Argument $codexCloudSyncArguments
    $codexCloudSyncTriggers = @(
        (New-ScheduledTaskTrigger -Daily -At '00:00' | ConvertTo-WslLocalTimeTrigger),
        (New-ScheduledTaskTrigger -Daily -At '12:00' | ConvertTo-WslLocalTimeTrigger)
    )
    $codexCloudSyncSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew
    $codexCloudSyncPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U

    $existingCodexCloudSyncTask = Get-ScheduledTask -TaskName $CodexCloudEnvironmentSyncTaskName -ErrorAction SilentlyContinue
    if ($existingCodexCloudSyncTask) {
        if ($PSCmdlet.ShouldProcess($CodexCloudEnvironmentSyncTaskName, 'Update scheduled task')) {
            Set-WslScheduledTask -TaskName $CodexCloudEnvironmentSyncTaskName -Action $codexCloudSyncAction -Trigger $codexCloudSyncTriggers `
                -Settings $codexCloudSyncSettings -Principal $codexCloudSyncPrincipal
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess($CodexCloudEnvironmentSyncTaskName, 'Register scheduled task')) {
            Register-WslScheduledTask -TaskName $CodexCloudEnvironmentSyncTaskName -Action $codexCloudSyncAction -Trigger $codexCloudSyncTriggers `
                -Settings $codexCloudSyncSettings -Principal $codexCloudSyncPrincipal
        }
    }

    # --- Catch-up settings shared by the daily wsl.exe publish tasks ---
    # Usage census and session miner run once a day; a laptop asleep at that minute used to
    # skip the day (Task Scheduler result 0x800710E0, 2147946720 - the source's Session Miner
    # went two days without a real run). StartWhenAvailable now runs the missed task once the
    # machine wakes. The pwsh tasks keep it off because they can die inside WSL's post-wake
    # transition window; these scripts only need a working wsl.exe, so a catch-up that lands in
    # that window and fails is retried (3 times, 10 minutes apart - past the ~270 s window)
    # instead.
    $catchUpSettingsParams = @{
        AllowStartIfOnBatteries    = $true
        DontStopIfGoingOnBatteries = $true
        StartWhenAvailable         = $true
        RestartCount               = 3
        RestartInterval            = New-TimeSpan -Minutes 10
        ExecutionTimeLimit         = New-TimeSpan -Minutes 15
        MultipleInstances          = 'IgnoreNew'
    }

    # --- Usage census publish: one daily trigger, wsl.exe as the action -----
    # Background-only like the Codex Cloud sync, but the action is wsl.exe DIRECTLY (no pwsh in
    # between) with --cd into the scripts directory and bash running the wrapper. As an S4U task
    # it runs in session 0, so no console window can ever appear. The owner's WSL git
    # authenticates through `gh auth git-credential` with a file-stored token, which works in an
    # S4U logon. StartWhenAvailable is on (see the catch-up settings above): a missed day is caught up on
    # wake, and the restart settings retry a run that hits WSL's post-wake window (see AGENTS.md). $ScriptsDir was trimmed of
    # any trailing backslash above, which would otherwise escape the closing quote.
    $usageCensusArguments = "--distribution $DistroName --cd `"$ScriptsDir`" --exec /bin/bash ./publish-usage-census.sh"
    $usageCensusAction = New-ScheduledTaskAction -Execute $WslExePath -Argument $usageCensusArguments
    $usageCensusTrigger = New-ScheduledTaskTrigger -Daily -At $UsageCensusTime | ConvertTo-WslLocalTimeTrigger
    $usageCensusSettings = New-ScheduledTaskSettingsSet @catchUpSettingsParams
    $usageCensusPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U

    $existingUsageCensusTask = Get-ScheduledTask -TaskName $UsageCensusTaskName -ErrorAction SilentlyContinue
    if ($existingUsageCensusTask) {
        if ($PSCmdlet.ShouldProcess($UsageCensusTaskName, 'Update scheduled task')) {
            Set-WslScheduledTask -TaskName $UsageCensusTaskName -Action $usageCensusAction -Trigger $usageCensusTrigger `
                -Settings $usageCensusSettings -Principal $usageCensusPrincipal
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess($UsageCensusTaskName, 'Register scheduled task')) {
            Register-WslScheduledTask -TaskName $UsageCensusTaskName -Action $usageCensusAction -Trigger $usageCensusTrigger `
                -Settings $usageCensusSettings -Principal $usageCensusPrincipal
        }
    }

    # --- Session miner: one daily trigger, wsl.exe as the action ------------
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
    $sessionMinerPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U

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

    # --- Memory curation: one weekly (Monday) trigger, wsl.exe as the action
    # Built like the session miner above (wsl.exe directly, S4U, session 0, no StartWhenAvailable):
    # a missed week is simply curated the next Monday. The wrapper bounds its own Claude run at 2
    # hours, so the task's limit of 3 hours only ever stops a wedged wrapper.
    $memoryCurationArguments = "--distribution $DistroName --cd `"$ScriptsDir`" --exec /bin/bash ./run-memory-curation.sh"
    $memoryCurationAction = New-ScheduledTaskAction -Execute $WslExePath -Argument $memoryCurationArguments
    $memoryCurationTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $MemoryCurationTime | ConvertTo-WslLocalTimeTrigger
    $memoryCurationSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew
    $memoryCurationPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U

    $existingMemoryCurationTask = Get-ScheduledTask -TaskName $MemoryCurationTaskName -ErrorAction SilentlyContinue
    if ($existingMemoryCurationTask) {
        if ($PSCmdlet.ShouldProcess($MemoryCurationTaskName, 'Update scheduled task')) {
            Set-WslScheduledTask -TaskName $MemoryCurationTaskName -Action $memoryCurationAction -Trigger $memoryCurationTrigger `
                -Settings $memoryCurationSettings -Principal $memoryCurationPrincipal
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess($MemoryCurationTaskName, 'Register scheduled task')) {
            Register-WslScheduledTask -TaskName $MemoryCurationTaskName -Action $memoryCurationAction -Trigger $memoryCurationTrigger `
                -Settings $memoryCurationSettings -Principal $memoryCurationPrincipal
        }
    }

    # --- Waiting feed publish: every minute, wsl.exe as the action ----------
    # Same shape as the usage census (wsl.exe directly, S4U, session 0), but repeating every
    # minute with the indefinite-repetition construction the ccstatusline trigger documents above
    # (-Once + creation-time -RepetitionInterval, no -RepetitionDuration). The script is cheap
    # when nothing changed, so a 5 minute limit is generous; IgnoreNew keeps a slow run (a hung
    # push) from stacking up behind itself. No StartWhenAvailable: the feed is a live view, so a
    # missed minute is just skipped.
    $waitingFeedArguments = "--distribution $DistroName --cd `"$ScriptsDir`" --exec /bin/bash ./publish-waiting-feed.sh"
    $waitingFeedAction = New-ScheduledTaskAction -Execute $WslExePath -Argument $waitingFeedArguments
    $waitingFeedTrigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).Date) `
        -RepetitionInterval (New-TimeSpan -Minutes 1) | ConvertTo-WslLocalTimeTrigger
    $waitingFeedSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew
    $waitingFeedPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U

    $existingWaitingFeedTask = Get-ScheduledTask -TaskName $WaitingFeedTaskName -ErrorAction SilentlyContinue
    if ($existingWaitingFeedTask) {
        if ($PSCmdlet.ShouldProcess($WaitingFeedTaskName, 'Update scheduled task')) {
            Set-WslScheduledTask -TaskName $WaitingFeedTaskName -Action $waitingFeedAction -Trigger $waitingFeedTrigger `
                -Settings $waitingFeedSettings -Principal $waitingFeedPrincipal
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess($WaitingFeedTaskName, 'Register scheduled task')) {
            Register-WslScheduledTask -TaskName $WaitingFeedTaskName -Action $waitingFeedAction -Trigger $waitingFeedTrigger `
                -Settings $waitingFeedSettings -Principal $waitingFeedPrincipal
        }
    }

    # --- Docker WSL integration watchdog: logon + every 30 minutes, conhost --headless ----------
    # Repairs Docker Desktop's WSL integration with the distro (and alerts when it cannot); see
    # Invoke-DockerWslIntegrationWatchdog and AGENTS.md. The action is conhost.exe --headless
    # wrapping pwsh: the task is Interactive (below), and --headless keeps that interactive run
    # from flashing a console window the way a bare pwsh would.
    $dockerWatchdogScriptPath = Join-Path $ScriptsDir 'ensure-docker-wsl-integration.ps1'
    $dockerWatchdogArguments = "--headless `"$PwshPath`" -NoProfile -File `"$dockerWatchdogScriptPath`" -DistroName $DistroName"
    $dockerWatchdogAction = New-ScheduledTaskAction -Execute $ConhostPath -Argument $dockerWatchdogArguments

    # Trigger 1: at logon of the current user, delayed so the check never races WSL's post-boot
    # init window (up to ~270 s) or Docker Desktop's own start at login (see AGENTS.md). Task
    # Scheduler wants the delay as an ISO 8601 duration; XmlConvert formats a non-round number
    # of minutes correctly too.
    $dockerWatchdogLogonTrigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME" | ConvertTo-WslLocalTimeTrigger
    $dockerWatchdogLogonTrigger.Delay = [System.Xml.XmlConvert]::ToString([timespan]::FromMinutes($DockerWatchdogLogonDelayMinutes))
    # Trigger 2: the same indefinite-repetition construction as the ccstatusline trigger above (-Once +
    # creation-time -RepetitionInterval, never mutated afterward). A repetition tick that lands
    # right after a boot is deferred by the function's own wake guard.
    $dockerWatchdogRepeatTrigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).Date) `
        -RepetitionInterval (New-TimeSpan -Minutes $DockerWatchdogIntervalMinutes) | ConvertTo-WslLocalTimeTrigger
    $dockerWatchdogTriggers = @($dockerWatchdogLogonTrigger, $dockerWatchdogRepeatTrigger)

    # No StartWhenAvailable: a missed tick is simply covered by the next one, and a catch-up at
    # wake would land in the post-wake transition window.
    $dockerWatchdogSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -MultipleInstances IgnoreNew
    # Interactive, not S4U, on purpose: 'docker desktop restart' relaunches the Docker Desktop
    # GUI, which must land in the user's session (an S4U task runs in session 0, where the GUI
    # would start unseen and without the user's desktop), and the alert toast needs the user's
    # desktop too. Still the current user, never SYSTEM.
    $dockerWatchdogPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

    $existingDockerWatchdogTask = Get-ScheduledTask -TaskName $DockerWatchdogTaskName -ErrorAction SilentlyContinue
    if ($existingDockerWatchdogTask) {
        if ($PSCmdlet.ShouldProcess($DockerWatchdogTaskName, 'Update scheduled task')) {
            Set-WslScheduledTask -TaskName $DockerWatchdogTaskName -Action $dockerWatchdogAction -Trigger $dockerWatchdogTriggers `
                -Settings $dockerWatchdogSettings -Principal $dockerWatchdogPrincipal
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess($DockerWatchdogTaskName, 'Register scheduled task')) {
            Register-WslScheduledTask -TaskName $DockerWatchdogTaskName -Action $dockerWatchdogAction -Trigger $dockerWatchdogTriggers `
                -Settings $dockerWatchdogSettings -Principal $dockerWatchdogPrincipal
        }
    }

    # --- Codex Cloud sync: disabled unless -EnableCodexTasks -----------------
    # It is registered or updated above exactly as always, so it exists and its definition stays
    # current, and only then switched. Enabling is explicit too, so passing -EnableCodexTasks
    # turns an already-disabled task back on. Re-running without the switch leaves it disabled.
    $codexTaskVerb = if ($EnableCodexTasks) { 'Enable' } else { 'Disable' }
    if ($PSCmdlet.ShouldProcess($CodexCloudEnvironmentSyncTaskName, "$codexTaskVerb scheduled task")) {
        Set-WslScheduledTaskEnabled -TaskName $CodexCloudEnvironmentSyncTaskName -Enabled ([bool]$EnableCodexTasks)
    }

    # --- Archive legacy scripts this module supersedes ----------------------
    $archiveTimestamp = Get-Date -Format 'yyyyMMdd'

    # When register-tasks.ps1 is invoked as `pwsh -File ... -LegacyScriptsToArchive
    # "C:\a.ps1","C:\b.ps1"` from another shell (notably Windows PowerShell 5.1), native-command
    # argument handling flattens the two array elements into ONE literal string
    # "C:\a.ps1,C:\b.ps1" before pwsh's -File mode ever sees it - -File never re-parses commas
    # into an array the way a real PowerShell-to-PowerShell call would. Test-Path then fails on
    # the joined string and archiving silently does nothing. Work around it by expanding any
    # element that is a comma-joined list of rooted Windows paths back into its parts; an element
    # without a comma, or whose comma-split fragments don't all look like rooted paths, is left
    # alone (a legitimate single path may itself contain a comma).
    $expandedLegacyScriptsToArchive = foreach ($rawLegacyPath in $LegacyScriptsToArchive) {
        if ($rawLegacyPath -notlike '*,*') {
            $rawLegacyPath
            continue
        }

        $legacyPathFragments = $rawLegacyPath -split ','
        $anyFragmentNotRooted = $legacyPathFragments | Where-Object {
            $_ -notmatch '^[A-Za-z]:[\\/]' -and $_ -notmatch '^\\\\'
        }

        if ($anyFragmentNotRooted) {
            $rawLegacyPath
        }
        else {
            $legacyPathFragments
        }
    }

    foreach ($legacyPath in $expandedLegacyScriptsToArchive) {
        if (-not (Test-Path -LiteralPath $legacyPath)) {
            $legacyLeafForMissingCheck = Split-Path -Path $legacyPath -Leaf
            $legacyParentForMissingCheck = Split-Path -Path $legacyPath -Parent
            $supersededSiblingPattern = "$legacyLeafForMissingCheck.superseded-*"
            $supersededSiblingPath = if ($legacyParentForMissingCheck) {
                Join-Path $legacyParentForMissingCheck $supersededSiblingPattern
            }
            else {
                $supersededSiblingPattern
            }

            # An idempotent re-run naturally hits this: a previous run already renamed the
            # legacy script out of the way, so it no longer exists at its original path. Only
            # warn when there's no evidence that already happened.
            if (-not (Test-Path -Path $supersededSiblingPath)) {
                Write-Warning "Legacy script not found, nothing archived: $legacyPath"
            }
            continue
        }

        $archiveName = (Split-Path -Path $legacyPath -Leaf) + ".superseded-$archiveTimestamp"
        $legacyParent = Split-Path -Path $legacyPath -Parent
        $archivePath = if ($legacyParent) { Join-Path $legacyParent $archiveName } else { $archiveName }

        if (Test-Path -LiteralPath $archivePath) {
            Write-Warning "Archive target already exists, skipping: $archivePath"
            continue
        }

        if ($PSCmdlet.ShouldProcess($legacyPath, "Rename to $archiveName")) {
            Rename-Item -LiteralPath $legacyPath -NewName $archiveName
        }
    }

    # --- Task Scheduler operational log (History tab) ----------------------
    # Disabled on a fresh Windows install. Without it a scheduled task leaves only its last
    # result code behind - no start/finish times, no per-run exit code, no record of a run that
    # was terminated at its execution time limit (see AGENTS.md's interactive-prompt section).
    # This is best-effort and never fatal: every task above has already been registered or
    # updated by the time this runs, so a failure here only warns.
    if ($SkipTaskHistory) {
        $taskHistoryResult = 'Skipped (-SkipTaskHistory)'
    }
    else {
        try {
            $taskHistoryResult = Enable-TaskSchedulerHistory -WhatIf:$WhatIfPreference -Confirm:$false
        }
        catch {
            Write-Warning "Failed to enable Task Scheduler history (Microsoft-Windows-TaskScheduler/Operational): $_"
            $taskHistoryResult = 'Failed'
        }
    }

    # --- Summary -------------------------------------------------------------
    $codexTaskState = if ($EnableCodexTasks) { 'enabled' } else { 'disabled; pass -EnableCodexTasks to enable' }
    Write-Information -MessageData "ccstatusline task '$CcstatuslineTaskName' (background/S4U): $ccstatuslineArguments (repeats every $CcstatuslineIntervalMinutes min, indefinitely)" -InformationAction Continue
    Write-Information -MessageData "Memory log task '$MemoryLogTaskName' (background/S4U): $memoryLogArguments (repeats every $MemoryLogIntervalMinutes min, indefinitely)" -InformationAction Continue
    Write-Information -MessageData "Codex Cloud task '$CodexCloudEnvironmentSyncTaskName' (background/S4U, $codexTaskState): $codexCloudSyncArguments (daily at 00:00 and 12:00)" -InformationAction Continue
    Write-Information -MessageData "Usage census task '$UsageCensusTaskName' (background/S4U): $WslExePath $usageCensusArguments (daily at $UsageCensusTime)" -InformationAction Continue
    Write-Information -MessageData "Session miner task '$SessionMinerTaskName' (background/S4U): $WslExePath $sessionMinerArguments (daily at $SessionMinerTime)" -InformationAction Continue
    Write-Information -MessageData "Memory curation task '$MemoryCurationTaskName' (background/S4U): $WslExePath $memoryCurationArguments (weekly on Monday at $MemoryCurationTime)" -InformationAction Continue
    Write-Information -MessageData "Waiting feed task '$WaitingFeedTaskName' (background/S4U): $WslExePath $waitingFeedArguments (repeats every 1 min, indefinitely)" -InformationAction Continue
    Write-Information -MessageData "Docker watchdog task '$DockerWatchdogTaskName' (interactive, headless): $ConhostPath $dockerWatchdogArguments (at logon after $DockerWatchdogLogonDelayMinutes min, then every $DockerWatchdogIntervalMinutes min, indefinitely)" -InformationAction Continue
    Write-Information -MessageData "Task Scheduler history (Microsoft-Windows-TaskScheduler/Operational): $taskHistoryResult" -InformationAction Continue
}
