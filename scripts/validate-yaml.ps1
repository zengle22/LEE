param(
  [string[]]$Files,
  [string]$Dir = "spec-global"
)
$ErrorActionPreference = 'Stop'
function Ensure-YamlModule {
  $m = Get-Module -ListAvailable -Name powershell-yaml
  if (-not $m) {
    try {
      try { Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser -Confirm:$false } catch {}
      Install-Module -Name powershell-yaml -Scope CurrentUser -Force -AllowClobber -Repository PSGallery
    } catch {
      Write-Output ("YAML validator install failed: " + $_.Exception.Message)
      exit 1
    }
  }
  Import-Module powershell-yaml -ErrorAction Stop
}
Ensure-YamlModule
$targets = if ($Files -and $Files.Length -gt 0) { $Files } else {
  Get-ChildItem -Path $Dir -Recurse -File -Include *.yaml, *.yml | ForEach-Object { $_.FullName }
}
$ok = 0
$fail = 0
foreach ($f in $targets) {
  try {
    $y = Get-Content -Raw -Path $f
    $null = $y | ConvertFrom-Yaml
    Write-Output ("YAML OK: " + $f)
    $ok++
  } catch {
    Write-Output ("YAML FAIL: " + $f + " -> " + $_.Exception.Message)
    $fail++
  }
}
Write-Output ("SUMMARY: OK=" + $ok + " FAIL=" + $fail)
if ($fail -gt 0) { exit 2 } else { exit 0 }
