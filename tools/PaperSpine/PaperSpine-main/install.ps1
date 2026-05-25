param(
    [ValidateSet("all", "codex", "claude", "openclaw")]
    [string]$Target = "all",
    [switch]$CleanLegacy
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$CodexSkill = Join-Path $Root "dist\codex\paper-spine"
$CodexSkills = Join-Path $Root "dist\codex\skills"
$ClaudeSkills = Join-Path $Root "dist\claude\skills"
$ClaudeCommands = Join-Path $Root "dist\claude\commands"
$OpenClawSkills = Join-Path $Root "dist\openclaw\skills"
$VersionManifest = Join-Path $Root "dist\paperspine_version.json"

function Assert-PathExists {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required path not found: $Path"
    }
}

function Reset-CopyDirectory {
    param(
        [string]$Source,
        [string]$Destination
    )
    Assert-PathExists $Source
    if (Test-Path -LiteralPath $Destination) {
        Remove-Item -LiteralPath $Destination -Recurse -Force
    }
    $parent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Remove-IfExists {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Get-PaperSpineConfigHome {
    if ($env:PAPERSPINE_CONFIG_HOME) {
        return $env:PAPERSPINE_CONFIG_HOME
    }
    return (Join-Path $HOME ".paperspine")
}

function Write-InstallState {
    param([string[]]$Targets)
    $configHome = Get-PaperSpineConfigHome
    New-Item -ItemType Directory -Force -Path $configHome | Out-Null
    $manifest = Get-Content -LiteralPath $VersionManifest -Raw | ConvertFrom-Json
    $state = [ordered]@{
        installed_version = $manifest.version
        installed_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
        source = [ordered]@{
            repository = $manifest.repository
            channel = $manifest.channel
            manifest_url = $manifest.manifest_url
            archive_url = $manifest.archive_url
        }
        targets = $Targets
        preserved_config_path = (Join-Path $configHome "config.json")
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $configHome "install_state.json") -Encoding UTF8
}

Assert-PathExists $CodexSkill
Assert-PathExists $CodexSkills
Assert-PathExists $ClaudeSkills
Assert-PathExists $ClaudeCommands
Assert-PathExists $OpenClawSkills
Assert-PathExists $VersionManifest

$installedTargets = @()

if ($Target -eq "all" -or $Target -eq "codex") {
    $codexSkillsDir = Join-Path $HOME ".codex\skills"
    if ($CleanLegacy) {
        Remove-IfExists (Join-Path $codexSkillsDir "PaperSpine")
        Remove-IfExists (Join-Path $codexSkillsDir "PaperSpineV2")
        Get-ChildItem -LiteralPath $codexSkillsDir -Directory -Filter "paper-spine*" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
    }
    Get-ChildItem -LiteralPath $CodexSkills -Directory | ForEach-Object {
        Reset-CopyDirectory $_.FullName (Join-Path $codexSkillsDir $_.Name)
    }
    Write-Output "Installed Codex skills: $codexSkillsDir"
    $installedTargets += "codex"
}

if ($Target -eq "all" -or $Target -eq "claude") {
    $claudeSkillsDir = Join-Path $HOME ".claude\skills"
    $claudeCommandsDir = Join-Path $HOME ".claude\commands"
    New-Item -ItemType Directory -Force -Path $claudeSkillsDir, $claudeCommandsDir | Out-Null

    if ($CleanLegacy) {
        Remove-IfExists (Join-Path $claudeSkillsDir "PaperSpine")
        Remove-IfExists (Join-Path $claudeSkillsDir "PaperSpineV2")
        Remove-IfExists (Join-Path $claudeSkillsDir "paper-writing-assistant")
        Get-ChildItem -LiteralPath $claudeSkillsDir -Directory -Filter "paper-spine*" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
        Remove-IfExists (Join-Path $claudeCommandsDir "paperspine.md")
        Remove-IfExists (Join-Path $claudeCommandsDir "paperspine-ui.md")
    }

    Get-ChildItem -LiteralPath $ClaudeSkills -Directory | ForEach-Object {
        Reset-CopyDirectory $_.FullName (Join-Path $claudeSkillsDir $_.Name)
    }
    Get-ChildItem -LiteralPath $ClaudeCommands -File -Filter "*.md" | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $claudeCommandsDir $_.Name) -Force
    }
    Write-Output "Installed Claude Code skills: $claudeSkillsDir"
    Write-Output "Installed Claude Code commands: $claudeCommandsDir"
    $installedTargets += "claude"
}

if ($Target -eq "all" -or $Target -eq "openclaw") {
    $openClawSkillsDir = Join-Path $HOME ".openclaw\skills"
    New-Item -ItemType Directory -Force -Path $openClawSkillsDir | Out-Null

    if ($CleanLegacy) {
        Remove-IfExists (Join-Path $openClawSkillsDir "PaperSpine")
        Remove-IfExists (Join-Path $openClawSkillsDir "PaperSpineV2")
        Get-ChildItem -LiteralPath $openClawSkillsDir -Directory -Filter "paper-spine*" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
    }

    Get-ChildItem -LiteralPath $OpenClawSkills -Directory | ForEach-Object {
        Reset-CopyDirectory $_.FullName (Join-Path $openClawSkillsDir $_.Name)
    }
    Write-Output "Installed OpenClaw skills: $openClawSkillsDir"
    $installedTargets += "openclaw"
}

# Hide internal PaperSpine skills from Claude Code / menu
$claudeSettingsPath = Join-Path $HOME ".claude\settings.json"
$settings = @{}
if (Test-Path -LiteralPath $claudeSettingsPath) {
    try { $settings = Get-Content -LiteralPath $claudeSettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable } catch { $settings = @{} }
}
if (-not $settings.ContainsKey("skillOverrides")) { $settings["skillOverrides"] = @{} }
$internalSkills = @("paper-spine")
foreach ($skill in $internalSkills) { $settings["skillOverrides"][$skill] = "off" }
$settings | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $claudeSettingsPath -Encoding UTF8
Write-Output "Updated skillOverrides in $claudeSettingsPath"

Write-InstallState $installedTargets
Write-Output "PaperSpine install complete. Restart Codex, Claude Code, or OpenClaw before use."
