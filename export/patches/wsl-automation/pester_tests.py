"""X10 in the Pester tests, and the tests of the kit's session miner task.

tests/Tasks.Tests.ps1
  - The -BackupDir/-ResticRepoDir fixture and the same two arguments on every
    Set-WslAutomationScheduledTasks call go (the parameters are gone).
  - Removed, because their subject is left out (X10): the backup task's Its
    (action, -Format, -ResticRepoDir, daily trigger, registration, WakeToRun,
    StartWhenAvailable, battery, limit, repetition, the two trailing-backslash
    Its) and its "already exists" Context; the keeper's Its (action,
    registration, interval); both launchers' Its, -CodexLauncherTaskName, and
    the Codex launcher's "already exists" Context.
  - Removed, because the task health publish is left out with its script
    (DECISIONS "Re-pin (2026-11-03)"): its four Its and its "already exists"
    Context.
  - Changed to the six tasks that remain: the S4U count (nine -> six, and
    the census and session miner principals' counts with it), the shared
    15 minute settings count (four -> two: the session miner keeps the
    kit's 30 minute limit and the task health task is gone), the no-WindowStyle check (the
    ccstatusline action only), the interactive-principal check (two -> none;
    the census task stands in for the backup as the S4U-for-the-current-user
    example), the history failure check (it names the census and ccstatusline
    tasks instead of the backup and keeper).
  - The AST bootstrap test discovers every `--exec /bin/bash ./<entry>.sh`
    action instead of naming each one, so any later wsl.exe task is covered
    without a list to update; its counts become six actions, six scripts.
  - The source's session miner registration It is replaced by the kit's,
    which asserts the kit's 07:17 time and 30 minute limit. The source's
    other session miner Its and its "already exists" Context are kept.

  - Re-pin round 9 (DECISIONS "Re-pin round 9"): the Claude settings sync's
    five Its and its "already exists" Context go (X9, its task is left out),
    and so does the source's whole -EnableCodexTasks Context, which tests the
    Codex launcher and the keeper's -NoCodexRemoteControl too; the kit's own
    Context, written for the Codex Cloud sync alone, replaces it. The memory
    log's Its and Context stay. The session miner's catch-up (the source's
    new shared settings) shows in the kit's registration It, and the shared
    settings counts name the usage census alone. The S4U count is seven
    (ccstatusline, memory log, Codex Cloud sync, census, session miner,
    memory curation, waiting feed), and the bootstrap coverage test counts
    eight script actions.

tests/Helpers.Tests.ps1
  Removed: the Describes for the backup lock (New-, Test-, Remove-WslBackupLock)
  and the two launcher argument builders, whose files are left out.

tests/RepoUpdate.Tests.ps1
  'Existing task entries fail open after checkout warnings' keeps its
  ccstatusline and Codex Cloud rows; the keeper and manual-backup entries,
  their mocks and parameters, and the keeper's dirty-branch It go.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("kit_wsl_text", Path(__file__).with_name("_text.py"))
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

TASKS = "tests/Tasks.Tests.ps1"
HELPERS = "tests/Helpers.Tests.ps1"
REPO_UPDATE = "tests/RepoUpdate.Tests.ps1"

DROPPED_ITS = [
    "It 'creates the backup task with a wsl-restic-backup.ps1 action",
    "It 'no longer schedules the wsl --export backup or passes -Format'",
    "It 'requires -ResticRepoDir'",
    "It 'creates the keeper task with an action",
    "It 'creates exactly one daily trigger for the backup task and no logon trigger",
    "It 'registers the backup task via Register-WslScheduledTask",
    "It 'registers the keeper task via Register-WslScheduledTask",
    "It 'registers the interactive launcher task",
    "It 'registers the interactive Codex remote control launcher task",
    "It 'honors -CodexLauncherTaskName'",
    "It 'configures the keeper task repetition interval",
    "It 'registers the backup task without -WakeToRun by default",
    "It 'registers the backup task with -WakeToRun when -WakeBackupToRun is set'",
    "It 'registers the backup task with StartWhenAvailable = $false",
    "It 'registers the backup task to run on battery",
    "It 'registers the backup task with a 2 hour limit",
    "It 'builds the backup trigger with Repetition.Interval PT1H",
    "It 'builds the backup trigger repetition interval from",
    "It 'sanitizes a trailing backslash in BackupDir",
    "It 'sanitizes a trailing backslash in ResticRepoDir",
    "It 'registers the session miner task as a direct wsl.exe action with one daily trigger, S4U, and catch-up with restarts'",
    "It 'creates the Claude settings sync task as a dry run by default",
    "It 'passes -Live to the Claude settings sync only when",
    "It 'registers the Claude settings sync as S4U, every 15 minutes",
    "It 'honors -ClaudeSettingsSyncTaskName and",
    "It 'registers nothing for the Claude settings sync under -WhatIf'",
    "It 'registers the task health task",
    "It 'builds the task health principal",
    "It 'honors -TaskHealthTime",
    "It 'sanitizes a trailing backslash in ScriptsDir so the task health",
]
DROPPED_CONTEXTS = [
    "Context 'when the backup task already exists'",
    "Context 'when the Codex remote control launcher task already exists'",
    "Context 'when the task health task already exists'",
    "Context 'when the Claude settings sync task already exists'",
    "Context 'Codex tasks are disabled unless -EnableCodexTasks is passed'",
]

FIXTURE_OLD = """        $script:scriptsDir = Join-Path $TestDrive 'scripts'
        $script:backupDir = Join-Path $TestDrive 'backups'
        $script:resticRepoDir = 'D:\\Backups\\wsl-restic'
        New-Item -ItemType Directory -Path $script:scriptsDir -Force | Out-Null
        New-Item -ItemType Directory -Path $script:backupDir -Force | Out-Null
"""
FIXTURE_NEW = """        $script:scriptsDir = Join-Path $TestDrive 'scripts'
        New-Item -ItemType Directory -Path $script:scriptsDir -Force | Out-Null
"""

ARGS_OLD = " -BackupDir $script:backupDir -ResticRepoDir $script:resticRepoDir `\n"
ARGS_NEW = " `\n"
EXPECTED_ARGS = 58  # -BackupDir/-ResticRepoDir argument lines left once the dropped Its and Contexts are gone

S4U_OLD = """        It 'runs all eleven background tasks as S4U in session 0, where no desktop window can flash' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:\\fake\\pwsh.exe' -Confirm:$false

            # The backup, keeper, ccstatusline sync, memory log, Claude settings sync, Codex Cloud sync, usage census, session miner,
            # memory curation, waiting feed publish, and task health publish are windowless background tasks.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 11 -Exactly -ParameterFilter {
"""
S4U_NEW = """        It 'runs all seven background tasks as S4U in session 0, where no desktop window can flash' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:\\fake\\pwsh.exe' -Confirm:$false

            # The ccstatusline sync, memory log, Codex Cloud sync, usage census, session miner,
            # memory curation and waiting feed publish are windowless background tasks.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 7 -Exactly -ParameterFilter {
"""

SHARED_SETTINGS_OLD = """            # Usage census, session miner and task health share the catch-up settings.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskSettingsSet -Times 3 -Exactly -ParameterFilter {
"""
SHARED_SETTINGS_NEW = """            # The usage census alone uses these 15 minute catch-up settings (the session miner
            # raises the limit to 30 minutes).
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskSettingsSet -Times 1 -Exactly -ParameterFilter {
"""

WINDOWSTYLE_OLD = """            $keeperAction = $script:capturedActions | Where-Object { $_.Argument -match 'ensure-claude-session\\.ps1' }
            $keeperAction.Argument | Should -Not -Match 'WindowStyle'
            $ccstatuslineAction"""
WINDOWSTYLE_NEW = """            $ccstatuslineAction"""
CLAUDE_WINDOWSTYLE = """            $claudeSettingsSyncAction = $script:capturedActions | Where-Object { $_.Argument -match 'sync-claude-settings\\.ps1' }
            $claudeSettingsSyncAction.Argument | Should -Not -Match 'WindowStyle'
"""

INTERACTIVE_OLD_START = "        It 'runs only the two launchers and the Docker watchdog interactively; the backup task is S4U for the current user, never SYSTEM' {\n"
INTERACTIVE_OLD_END = "        It 'creates the ccstatusline sync task with an action"
INTERACTIVE_NEW = """        It 'runs only the Docker watchdog interactively; the usage census task is S4U for the current user, never SYSTEM' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:\\fake\\pwsh.exe' -Confirm:$false

            # The Docker watchdog must restart Docker Desktop in the user's session; every other
            # task runs in the background.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 1 -Exactly -ParameterFilter {
                $LogonType -eq 'Interactive'
            }
            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'Usage Census Publish' -and
                $Principal.LogonType -eq 'S4U' -and $Principal.UserId -eq "$env:USERDOMAIN\\$env:USERNAME"
            }
        }

"""

CENSUS_PRINCIPAL_OLD = """            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 11 -Exactly -ParameterFilter {
                $LogonType -eq 'S4U' -and $UserId -eq "$env:USERDOMAIN\\$env:USERNAME"
"""
CENSUS_PRINCIPAL_NEW = """            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 7 -Exactly -ParameterFilter {
                $LogonType -eq 'S4U' -and $UserId -eq "$env:USERDOMAIN\\$env:USERNAME"
"""

MINER_ITS_ANCHOR = "        It 'builds the session miner principal for the current user, never SYSTEM, as S4U' {\n"
MINER_ITS = """        It 'registers the session miner task as a direct wsl.exe action with one daily trigger, S4U, a 30 minute limit, and catch-up with restarts' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:\\fake\\pwsh.exe' -Confirm:$false

            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'Session Miner' -and
                $Action.Execute -like '*wsl.exe' -and
                @($Trigger).Count -eq 1 -and $Trigger.IsDaily -and $Trigger.At -eq '07:17' -and
                $Principal.FakePrincipal -and $Principal.LogonType -eq 'S4U' -and
                $Principal.UserId -eq "$env:USERDOMAIN\\$env:USERNAME" -and
                $Settings.ExecutionTimeLimit.TotalMinutes -eq 30 -and $Settings.MultipleInstances -eq 'IgnoreNew' -and
                $Settings.DisallowStartIfOnBatteries -eq $false -and $Settings.StopIfGoingOnBatteries -eq $false -and
                $Settings.StartWhenAvailable -and $Settings.RestartCount -eq 3 -and $Settings.RestartInterval.TotalMinutes -eq 10
            }

            $minerAction = @($script:capturedActions | Where-Object { $_.Argument -match 'run-session-miner\\.sh' })
            $minerAction.Count | Should -Be 1
            $minerAction[0].Argument | Should -Match '--distribution Ubuntu'
            $minerAction[0].Argument.Contains('--cd "' + $script:scriptsDir + '"') | Should -BeTrue
            $minerAction[0].Argument | Should -Match '--exec /bin/bash \\./run-session-miner\\.sh$'
            $minerAction[0].Argument | Should -Not -Match 'pwsh'
        }

"""

HISTORY_OLD = """            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'WSL Ubuntu Daily Backup'
            }
            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'Claude Code Session Keeper'
            }
"""
HISTORY_NEW = """            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'Usage Census Publish'
            }
            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'ccstatusline Config Sync'
            }
"""

DISCOVERY_OLD = """                if ($expanded.Value.EndsWith('--exec /bin/bash ./publish-usage-census.sh')) { 'publish-usage-census.sh' }
                if ($expanded.Value.EndsWith('--exec /bin/bash ./run-session-miner.sh')) { 'run-session-miner.sh' }
                if ($expanded.Value.EndsWith('--exec /bin/bash ./run-memory-curation.sh')) { 'run-memory-curation.sh' }
                if ($expanded.Value.EndsWith('--exec /bin/bash ./publish-waiting-feed.sh')) { 'publish-waiting-feed.sh' }
                if ($expanded.Value.EndsWith('--exec /bin/bash ./publish-task-health.sh')) { 'publish-task-health.sh' }
"""
DISCOVERY_NEW = """                # Every wsl.exe action runs one Bash entry from the scripts directory; discover it by
                # shape, so a wsl.exe task added later is covered without editing this test.
                if ($expanded.Value -match '--exec /bin/bash \\./([A-Za-z0-9._-]+\\.sh)$') { $Matches[1] }
"""

COVERS_OLD = """    It 'covers all twelve script actions among fourteen registered task actions' {
        $script:actionCount | Should -Be 14
        $script:actionScripts.Count | Should -Be 12
        @($script:actionScripts | Sort-Object) | Should -Be @(
            'ensure-claude-session.ps1', 'ensure-docker-wsl-integration.ps1', 'log-wsl-memory.ps1', 'publish-task-health.sh', 'publish-usage-census.sh', 'publish-waiting-feed.sh', 'run-memory-curation.sh', 'run-session-miner.sh',
            'sync-ccstatusline-config.ps1', 'sync-claude-settings.ps1', 'sync-codex-cloud-environments.ps1', 'wsl-restic-backup.ps1'
        )
"""
COVERS_NEW = """    It 'covers all eight script actions among eight registered task actions' {
        $script:actionCount | Should -Be 8
        $script:actionScripts.Count | Should -Be 8
        @($script:actionScripts | Sort-Object) | Should -Be @(
            'ensure-docker-wsl-integration.ps1', 'log-wsl-memory.ps1', 'publish-usage-census.sh', 'publish-waiting-feed.sh', 'run-memory-curation.sh', 'run-session-miner.sh',
            'sync-ccstatusline-config.ps1', 'sync-codex-cloud-environments.ps1'
        )
"""

FOREACH_OLD = """        @{ Entry = 'ensure-claude-session.ps1'; Work = 'Invoke-ClaudeSessionKeeper' },
        @{ Entry = 'ensure-docker-wsl-integration.ps1'; Work = 'Invoke-DockerWslIntegrationWatchdog' },
        @{ Entry = 'log-wsl-memory.ps1'; Work = 'Write-WslMemorySample' },
        @{ Entry = 'sync-ccstatusline-config.ps1'; Work = 'Update-CcstatuslineConfig' },
        @{ Entry = 'sync-claude-settings.ps1'; Work = 'Invoke-ClaudeSettingsSync' },
        @{ Entry = 'sync-codex-cloud-environments.ps1'; Work = 'Invoke-CodexCloudEnvironmentSync' },
        @{ Entry = 'wsl-restic-backup.ps1'; Work = 'Invoke-WslResticBackup' }
"""
FOREACH_NEW = """        @{ Entry = 'ensure-docker-wsl-integration.ps1'; Work = 'Invoke-DockerWslIntegrationWatchdog' },
        @{ Entry = 'log-wsl-memory.ps1'; Work = 'Write-WslMemorySample' },
        @{ Entry = 'sync-ccstatusline-config.ps1'; Work = 'Update-CcstatuslineConfig' },
        @{ Entry = 'sync-codex-cloud-environments.ps1'; Work = 'Invoke-CodexCloudEnvironmentSync' }
"""

LEGACY_CONTEXT_ANCHOR = "    Context 'legacy script archiving' {\n"
CODEX_CONTEXT = r"""    Context 'The Codex Cloud sync is disabled unless -EnableCodexTasks is passed' {

        BeforeEach {
            # Records the order of registrations and enable/disable calls, so the task is shown to
            # be registered (or updated) first and switched afterward.
            $script:callOrder = [System.Collections.Generic.List[string]]::new()
            Mock -ModuleName WslAutomation Register-WslScheduledTask { $script:callOrder.Add("register:$TaskName") }
            Mock -ModuleName WslAutomation Set-WslScheduledTask { $script:callOrder.Add("update:$TaskName") }
            Mock -ModuleName WslAutomation Set-WslScheduledTaskEnabled { $script:callOrder.Add("enabled=${Enabled}:$TaskName") }
            Mock -ModuleName WslAutomation Get-ScheduledTask { $null }
        }

        It 'registers the Codex Cloud sync and then disables it by default' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -Confirm:$false

            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 1 -Exactly -ParameterFilter { $TaskName -eq 'Codex Cloud Environment Sync' }
            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 1 -Exactly
            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'Codex Cloud Environment Sync' -and $Enabled -eq $false
            }
            $script:callOrder.IndexOf('register:Codex Cloud Environment Sync') | Should -BeLessThan $script:callOrder.IndexOf('enabled=False:Codex Cloud Environment Sync')
        }

        It 'enables the Codex Cloud sync with -EnableCodexTasks' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -EnableCodexTasks -Confirm:$false

            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 1 -Exactly
            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'Codex Cloud Environment Sync' -and $Enabled -eq $true
            }
        }

        It 'honors -CodexCloudEnvironmentSyncTaskName when switching' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -CodexCloudEnvironmentSyncTaskName 'My Codex Sync' -Confirm:$false

            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'My Codex Sync' -and $Enabled -eq $false
            }
        }

        It 'updates an already-registered Codex Cloud sync in place and then disables it by default' {
            Mock -ModuleName WslAutomation Get-ScheduledTask {
                if ($TaskName -eq 'Codex Cloud Environment Sync') {
                    return [pscustomobject]@{ TaskName = $TaskName; State = 'Disabled' }
                }
                return $null
            }

            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -Confirm:$false

            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 0 -Exactly -ParameterFilter { $TaskName -like 'Codex*' }
            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTask -Times 1 -Exactly -ParameterFilter { $TaskName -eq 'Codex Cloud Environment Sync' }
            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 1 -Exactly -ParameterFilter { $Enabled -eq $false }
            $script:callOrder.IndexOf('update:Codex Cloud Environment Sync') | Should -BeLessThan $script:callOrder.IndexOf('enabled=False:Codex Cloud Environment Sync')
        }

        It 'enables an already-registered, disabled Codex Cloud sync when -EnableCodexTasks is passed' {
            Mock -ModuleName WslAutomation Get-ScheduledTask {
                if ($TaskName -eq 'Codex Cloud Environment Sync') {
                    return [pscustomobject]@{ TaskName = $TaskName; State = 'Disabled' }
                }
                return $null
            }

            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -EnableCodexTasks -Confirm:$false

            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 1 -Exactly -ParameterFilter { $Enabled -eq $true }
            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 0 -Exactly -ParameterFilter { $Enabled -eq $false }
        }

        It 'neither disables nor enables anything under -WhatIf' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -WhatIf | Out-Null
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -EnableCodexTasks -WhatIf | Out-Null

            Should -Invoke -ModuleName WslAutomation Set-WslScheduledTaskEnabled -Times 0 -Exactly
        }

        It 'says in the summary whether the Codex Cloud sync is enabled or disabled' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -Confirm:$false -InformationVariable disabledInfo | Out-Null
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:ake\pwsh.exe' -EnableCodexTasks -Confirm:$false -InformationVariable enabledInfo | Out-Null

            $disabledCodexLines = @($disabledInfo | ForEach-Object { "$_" } | Where-Object { $_ -match '^Codex Cloud task' })
            $disabledCodexLines.Count | Should -Be 1
            $disabledCodexLines | ForEach-Object { $_ | Should -Match '\(.*disabled; pass -EnableCodexTasks to enable' }

            $enabledCodexLines = @($enabledInfo | ForEach-Object { "$_" } | Where-Object { $_ -match '^Codex Cloud task' })
            $enabledCodexLines.Count | Should -Be 1
            $enabledCodexLines | ForEach-Object { $_ | Should -Match ', enabled\)' }
        }
    }

"""


def _tasks(text: str, where: str) -> str:
    for opener in DROPPED_ITS:
        text = T.drop_block(text, opener, where, " " * 8)
    for opener in DROPPED_CONTEXTS:
        text = T.drop_block(text, opener, where, " " * 4)
    text = T.sub_once(text, FIXTURE_OLD, FIXTURE_NEW, where)
    n = text.count(ARGS_OLD)
    if n != EXPECTED_ARGS:
        raise T.PatchError(f"{where}: expected {EXPECTED_ARGS} -BackupDir/-ResticRepoDir argument lines after the removals, found {n}")
    text = text.replace(ARGS_OLD, ARGS_NEW)
    text = T.sub_once(text, S4U_OLD, S4U_NEW, where)
    text = T.sub_once(text, WINDOWSTYLE_OLD, WINDOWSTYLE_NEW, where)
    text = T.sub_once(text, CLAUDE_WINDOWSTYLE, "", where)
    text = T.replace_between(text, INTERACTIVE_OLD_START, INTERACTIVE_OLD_END, INTERACTIVE_NEW, where)
    # The census and the session miner principal Its both count the S4U principals.
    if text.count(CENSUS_PRINCIPAL_OLD) != 2:
        raise T.PatchError(f"{where}: expected 2 S4U principal counts, found {text.count(CENSUS_PRINCIPAL_OLD)}")
    text = text.replace(CENSUS_PRINCIPAL_OLD, CENSUS_PRINCIPAL_NEW)
    # The Codex Cloud and usage census Its both count the shared 15 minute settings.
    if text.count(SHARED_SETTINGS_OLD) != 2:
        raise T.PatchError(f"{where}: expected 2 shared settings counts, found {text.count(SHARED_SETTINGS_OLD)}")
    text = text.replace(SHARED_SETTINGS_OLD, SHARED_SETTINGS_NEW)
    text = T.sub_once(text, MINER_ITS_ANCHOR, MINER_ITS + MINER_ITS_ANCHOR, where)
    text = T.sub_once(text, HISTORY_OLD, HISTORY_NEW, where)
    text = T.sub_once(text, DISCOVERY_OLD, DISCOVERY_NEW, where)
    text = T.sub_once(text, COVERS_OLD, COVERS_NEW, where)
    text = T.sub_once(text, FOREACH_OLD, FOREACH_NEW, where)
    text = T.sub_once(text, LEGACY_CONTEXT_ANCHOR, CODEX_CONTEXT + LEGACY_CONTEXT_ANCHOR, where)
    for gone in ("BackupDir", "ResticRepoDir", "backupDir", "resticRepoDir", "Keeper", "keeper",
                 "Launcher", "wt.exe", "restic", "WakeBackupToRun", "WSL Ubuntu Daily Backup",
                 "TaskHealth", "task-health", "task health", "Task Health",
                 "ClaudeSettingsSync", "sync-claude-settings", "Claude Settings", "Claude settings",
                 "NoCodexRemoteControl"):
        if gone in text:
            raise T.PatchError(f"{where}: {gone!r} is still mentioned")
    return text


def _helpers(text: str, where: str) -> str:
    for name in ("New-WslBackupLock", "Test-WslBackupLock", "Remove-WslBackupLock",
                 "Get-ClaudeSessionWtArgumentList", "Get-CodexRemoteControlWtArgumentList"):
        text = T.drop_block(text, f"Describe '{name}' {{", where, " " * 4)
    for gone in ("BackupLock", "WtArgumentList"):
        if gone in text:
            raise T.PatchError(f"{where}: {gone!r} is still mentioned")
    return text


def _repo_update(text: str, where: str) -> str:
    text = T.sub_once(
        text,
        "foreach ($entry in @('ensure-claude-session.ps1', 'sync-ccstatusline-config.ps1', 'sync-codex-cloud-environments.ps1', 'wsl-ubuntu-backup.ps1')) {",
        "foreach ($entry in @('sync-ccstatusline-config.ps1', 'sync-codex-cloud-environments.ps1')) {",
        where,
    )
    text = T.sub_once(
        text,
        "        # No task may reach any real distro, session launcher, config file, or backup.\n"
        "        Mock Invoke-ClaudeSessionKeeper { [pscustomobject]@{ Status = 'AlreadyRunning'; WaitedSeconds = 0; ResumedSessionCount = 0; CodexRemoteControlLaunched = $false } }\n",
        "        # No task may reach any real distro, config file, or Codex Cloud environment.\n",
        where,
    )
    text = T.sub_once(text, "        Mock Invoke-WslBackup { [pscustomobject]@{ Status = 'Deferred'; FilePath = '' } }\n", "", where)
    text = T.sub_once(
        text,
        "        @{ Entry = 'ensure-claude-session.ps1'; Work = 'Invoke-ClaudeSessionKeeper' },\n"
        "        @{ Entry = 'sync-ccstatusline-config.ps1'; Work = 'Update-CcstatuslineConfig' },\n"
        "        @{ Entry = 'sync-codex-cloud-environments.ps1'; Work = 'Invoke-CodexCloudEnvironmentSync' },\n"
        "        @{ Entry = 'wsl-ubuntu-backup.ps1'; Work = 'Invoke-WslBackup' }\n",
        "        @{ Entry = 'sync-ccstatusline-config.ps1'; Work = 'Update-CcstatuslineConfig' },\n"
        "        @{ Entry = 'sync-codex-cloud-environments.ps1'; Work = 'Invoke-CodexCloudEnvironmentSync' }\n",
        where,
    )
    text = T.sub_once(
        text,
        "        if ($Entry -eq 'wsl-ubuntu-backup.ps1') { $parameters.BackupDir = 'C:\\example'; $parameters.NoPause = $true }\n",
        "",
        where,
    )
    text = T.drop_block(text, "It 'continues the keeper on a dirty feature branch without switching or merging' {", where, " " * 4)
    for gone in ("ensure-claude-session", "wsl-ubuntu-backup", "Invoke-ClaudeSessionKeeper", "Invoke-WslBackup"):
        if gone in text:
            raise T.PatchError(f"{where}: {gone!r} is still mentioned")
    return text


def apply(root: Path, ctx) -> None:
    T.edit_file(root, TASKS, _tasks)
    T.edit_file(root, HELPERS, _helpers)
    T.edit_file(root, REPO_UPDATE, _repo_update)
    for rel in (TASKS, HELPERS, REPO_UPDATE):
        T.check_ascii(root, rel)
