$configPath = "$env:USERPROFILE\.claude\settings.json"
$backupPath = "$configPath.backup"

# Backup current config
if (Test-Path $configPath) {
    Copy-Item $configPath $backupPath -Force
    Write-Host "Backup created: $backupPath"
}

# Create clean config
$config = @"
{
  "enabledPlugins": {
    "glm-plan-bug@zai-coding-plugins": true,
    "glm-plan-usage@zai-coding-plugins": true
  },
  "permissions": {
    "allow": [
      "mcp__pencil"
    ]
  }
}
"@

Set-Content -Path $configPath -Value $config -Force
Write-Host "Configuration fixed successfully!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Close all Claude Code terminals"
Write-Host "2. Open new terminal and run: claude"
Write-Host "3. Complete browser login"
