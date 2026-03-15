# LEE Auto Bug Fix Monitor
# 每分钟检查 output/bugs 目录，自动修复 open 状态的 bug

$BugDir = "e:\ai\LEE\output\bugs"
$LogDir = "e:\ai\LEE\output\logs\bug-monitor"
$LeePath = "e:\ai\LEE"

# 创建日志目录
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] $Message"
    Write-Host $logLine

    $logFile = "$LogDir\bug-monitor-$(Get-Date -Format 'yyyy-MM-dd').log"
    Add-Content -Path $logFile -Value $logLine
}

function Get-OpenBugs {
    $openBugs = @()
    $bugFiles = Get-ChildItem -Path $BugDir -Filter "*.md" -ErrorAction SilentlyContinue

    foreach ($file in $bugFiles) {
        $content = Get-Content $file.FullName -Raw
        if ($content -match '^status:\s*open') {
            $openBugs += $file.FullName
        }
    }
    return $openBugs
}

function Repair-Bug {
    param([string]$BugFile)

    Write-Log "开始修复 Bug: $BugFile"

    # 设置工作目录
    $originalLocation = Get-Location
    Set-Location $LeePath

    try {
        # 调用 lee dev.bug_fix 工作流
        $result = & lee run dev.bug_fix --bug-contract $BugFile 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            Write-Log "Bug 修复成功: $BugFile"

            # 更新 bug 状态为 fixed
            $content = Get-Content $BugFile -Raw
            $content = $content -replace '^status:\s*open', 'status: fixed'
            Set-Content -Path $BugFile -Value $content -NoNewline

            Write-Log "Bug 状态已更新为 fixed"
            return $true
        } else {
            Write-Log "Bug 修复失败 (exit code: $exitCode): $BugFile"
            Write-Log "输出: $result"
            return $false
        }
    } catch {
        Write-Log "Bug 修复异常：$_"
        return $false
    } finally {
        Set-Location $originalLocation
    }
}

# 主循环
Write-Log "=== Bug 监控服务启动 ==="
Write-Log "监控目录：$BugDir"
Write-Log "检查频率：每分钟一次"

while ($true) {
    try {
        $openBugs = Get-OpenBugs

        if ($openBugs.Count -gt 0) {
            Write-Log "发现 $($openBugs.Count) 个 open 状态的 Bug"

            foreach ($bugFile in $openBugs) {
                Repair-Bug -BugFile $bugFile
            }
        } else {
            Write-Log "没有发现 open 状态的 Bug"
        }
    } catch {
        Write-Log "主循环异常：$_"
    }

    # 等待 60 秒
    Start-Sleep -Seconds 60
}
