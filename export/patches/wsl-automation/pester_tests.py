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
    "It 'creates exactly one daily trigger for the backup task and no logon trigger'",
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
    "It 'registers the session miner task as a direct wsl.exe action with one daily trigger, S4U, and no catch-up setting'",
    "It 'registers the task health task",
    "It 'builds the task health principal",
    "It 'honors -TaskHealthTime",
    "It 'sanitizes a trailing backslash in ScriptsDir so the task health",
]
DROPPED_CONTEXTS = [
    "Context 'when the backup task already exists'",
    "Context 'when the Codex remote control launcher task already exists'",
    "Context 'when the task health task already exists'",
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

S4U_OLD = """        It 'runs all nine background tasks as S4U in session 0, where no desktop window can flash' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:\\fake\\pwsh.exe' -Confirm:$false

            # The backup, keeper, ccstatusline sync, Codex Cloud sync, usage census, session miner, memory curation,
            # waiting feed publish, and task health publish are windowless background tasks.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 9 -Exactly -ParameterFilter {
"""
S4U_NEW = """        It 'runs all six background tasks as S4U in session 0, where no desktop window can flash' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:\\fake\\pwsh.exe' -Confirm:$false

            # The ccstatusline sync, Codex Cloud sync, usage census, session miner, memory curation
            # and waiting feed publish are windowless background tasks.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 6 -Exactly -ParameterFilter {
"""

SHARED_SETTINGS_OLD = """            # The Codex Cloud sync, usage census, session miner, and task health tasks share these settings.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskSettingsSet -Times 4 -Exactly -ParameterFilter {
"""
SHARED_SETTINGS_NEW = """            # The Codex Cloud sync and usage census tasks share these settings.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskSettingsSet -Times 2 -Exactly -ParameterFilter {
"""

WINDOWSTYLE_OLD = """            $keeperAction = $script:capturedActions | Where-Object { $_.Argument -match 'ensure-claude-session\\.ps1' }
            $keeperAction.Argument | Should -Not -Match 'WindowStyle'
            $ccstatuslineAction"""
WINDOWSTYLE_NEW = """            $ccstatuslineAction"""

INTERACTIVE_OLD_START = "        It 'runs only the two launchers interactively; the backup task is S4U for the current user, never SYSTEM' {\n"
INTERACTIVE_OLD_END = "        It 'creates the ccstatusline sync task with an action"
INTERACTIVE_NEW = """        It 'runs no task interactively; the usage census task is S4U for the current user, never SYSTEM' {
            Set-WslAutomationScheduledTasks -ScriptsDir $script:scriptsDir `
                -PwshPath 'C:\\fake\\pwsh.exe' -Confirm:$false

            # Every task runs in the background; none needs to show a window.
            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 0 -Exactly -ParameterFilter {
                $LogonType -eq 'Interactive'
            }
            Should -Invoke -ModuleName WslAutomation Register-WslScheduledTask -Times 1 -Exactly -ParameterFilter {
                $TaskName -eq 'Usage Census Publish' -and
                $Principal.LogonType -eq 'S4U' -and $Principal.UserId -eq "$env:USERDOMAIN\\$env:USERNAME"
            }
        }

"""

CENSUS_PRINCIPAL_OLD = """            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 9 -Exactly -ParameterFilter {
                $LogonType -eq 'S4U' -and $UserId -eq "$env:USERDOMAIN\\$env:USERNAME"
"""
CENSUS_PRINCIPAL_NEW = """            Should -Invoke -ModuleName WslAutomation New-ScheduledTaskPrincipal -Times 6 -Exactly -ParameterFilter {
                $LogonType -eq 'S4U' -and $UserId -eq "$env:USERDOMAIN\\$env:USERNAME"
"""

MINER_ITS_ANCHOR = "        It 'builds the session miner principal for the current user, never SYSTEM, as S4U' {\n"
MINER_ITS = """        It 'registers the session miner task as a direct wsl.exe action with one daily trigger, S4U, a 30 minute limit, and no catch-up setting' {
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
                -not $Settings.StartWhenAvailable
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

COVERS_OLD = """    It 'covers all nine script actions among eleven registered task actions' {
        $script:actionCount | Should -Be 11
        $script:actionScripts.Count | Should -Be 9
        @($script:actionScripts | Sort-Object) | Should -Be @(
            'ensure-claude-session.ps1', 'publish-task-health.sh', 'publish-usage-census.sh', 'publish-waiting-feed.sh', 'run-memory-curation.sh', 'run-session-miner.sh',
            'sync-ccstatusline-config.ps1', 'sync-codex-cloud-environments.ps1', 'wsl-restic-backup.ps1'
        )
"""
COVERS_NEW = """    It 'covers all six script actions among six registered task actions' {
        $script:actionCount | Should -Be 6
        $script:actionScripts.Count | Should -Be 6
        @($script:actionScripts | Sort-Object) | Should -Be @(
            'publish-usage-census.sh', 'publish-waiting-feed.sh', 'run-memory-curation.sh', 'run-session-miner.sh',
            'sync-ccstatusline-config.ps1', 'sync-codex-cloud-environments.ps1'
        )
"""

FOREACH_OLD = """        @{ Entry = 'ensure-claude-session.ps1'; Work = 'Invoke-ClaudeSessionKeeper' },
        @{ Entry = 'sync-ccstatusline-config.ps1'; Work = 'Update-CcstatuslineConfig' },
        @{ Entry = 'sync-codex-cloud-environments.ps1'; Work = 'Invoke-CodexCloudEnvironmentSync' },
        @{ Entry = 'wsl-restic-backup.ps1'; Work = 'Invoke-WslResticBackup' }
"""
FOREACH_NEW = """        @{ Entry = 'sync-ccstatusline-config.ps1'; Work = 'Update-CcstatuslineConfig' },
        @{ Entry = 'sync-codex-cloud-environments.ps1'; Work = 'Invoke-CodexCloudEnvironmentSync' }
"""


def _tasks(text: str, where: str) -> str:
    for opener in DROPPED_ITS:
        text = T.drop_block(text, opener, where, " " * 8)
    for opener in DROPPED_CONTEXTS:
        text = T.drop_block(text, opener, where, " " * 4)
    text = T.sub_once(text, FIXTURE_OLD, FIXTURE_NEW, where)
    n = text.count(ARGS_OLD)
    if n != 44:
        raise T.PatchError(f"{where}: expected 44 -BackupDir/-ResticRepoDir argument lines after the removals, found {n}")
    text = text.replace(ARGS_OLD, ARGS_NEW)
    text = T.sub_once(text, S4U_OLD, S4U_NEW, where)
    text = T.sub_once(text, WINDOWSTYLE_OLD, WINDOWSTYLE_NEW, where)
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
    for gone in ("BackupDir", "ResticRepoDir", "backupDir", "resticRepoDir", "Keeper", "keeper",
                 "Launcher", "wt.exe", "restic", "WakeBackupToRun", "WSL Ubuntu Daily Backup",
                 "TaskHealth", "task-health", "task health", "Task Health"):
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
