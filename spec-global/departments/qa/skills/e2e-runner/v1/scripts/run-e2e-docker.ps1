# E2E Docker Runner - PowerShell Wrapper for Claude Code
# 这个脚本将 Docker 命令的输出保存到文件，解决 Bash tool 输出捕获问题

param(
    [string]$WorkDir = (Get-Location).Path,
    [string]$TestSpec = "e2e/quick-test.spec.ts",
    [string]$BaseUrl = "http://localhost:3002",
    [string]$ApiUrl = "http://localhost:8081/v1",
    [string]$DockerImage = "e2e-runner:latest"
)

$ErrorActionPreference = "Continue"

# 配置
$OutputDir = "$WorkDir\output"
$LogFile = "$OutputDir\docker-execution.log"
$TestResultFile = "$OutputDir\test-result.txt"
$RawOutputFile = "$OutputDir\test-output.raw"

# 创建输出目录
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# 日志函数
function Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    Write-Host $LogMessage
}

# 开始执行
Log "=========================================="
Log "  E2E Docker Runner (PowerShell)"
Log "=========================================="
Log ""
Log "配置:"
Log "  工作目录: $WorkDir"
Log "  测试用例: $TestSpec"
Log "  Base URL: $BaseUrl"
Log "  API URL: $ApiUrl"
Log "  Docker 镜像: $DockerImage"
Log ""

# 检查 Docker 镜像
Log "检查 Docker 镜像..."
$ImageExists = docker images | Select-String $DockerImage
if (-not $ImageExists) {
    Log "❌ Docker 镜像不存在: $DockerImage"
    "ERROR: Docker image not found" | Out-File -FilePath $TestResultFile -Encoding utf8
    exit 1
}
Log "✅ Docker 镜像存在"

# 检查测试文件
Log "检查测试文件..."
$TestFilePath = "$WorkDir\$TestSpec" -replace '/', '\'
if (-not (Test-Path $TestFilePath)) {
    Log "❌ 测试文件不存在: $TestFilePath"
    "ERROR: Test file not found" | Out-File -FilePath $TestResultFile -Encoding utf8
    exit 1
}
Log "✅ 测试文件存在"

# 执行测试
Log ""
Log "开始执行测试..."
Log "=========================================="

# 构建 Docker 命令（一行，避免 PowerShell 换行问题）
# 不指定 --reporter，使用配置文件中的所有 reporter（list, html, json, junit）
$DockerCommand = "docker run --rm --network host -e BASE_URL=""$BaseUrl"" -e API_URL=""$ApiUrl"" -v ""${WorkDir}:/work"" -w /work $DockerImage npx playwright test $TestSpec"

Log "执行命令:"
Log $DockerCommand
Log ""

# 运行 Docker 命令，将输出保存到文件
cmd /c $DockerCommand | Tee-Object -FilePath $RawOutputFile
$ExitCode = $LASTEXITCODE

Log ""
Log "=========================================="
Log "测试执行完成"
Log "退出码: $ExitCode"
Log "=========================================="

# 保存结果摘要
$Timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
@"
E2E_TEST_EXIT_CODE=$ExitCode
E2E_TEST_TIMESTAMP=$Timestamp
E2E_TEST_SPEC=$TestSpec
E2E_BASE_URL=$BaseUrl
E2E_API_URL=$ApiUrl
"@ | Out-File -FilePath $TestResultFile -Encoding utf8

# 判定结果
if ($ExitCode -eq 0) {
    Log "✅ 测试通过"
    Add-Content -Path $TestResultFile -Value "E2E_TEST_STATUS=PASS"
} else {
    Log "⚠️ 测试失败或存在错误"
    Add-Content -Path $TestResultFile -Value "E2E_TEST_STATUS=FAIL"
}

# 列出生成的文件
Log ""
Log "生成的文件:"
$TestResultsDir = "$OutputDir\test-results"
if (Test-Path $TestResultsDir) {
    Get-ChildItem -Path $TestResultsDir -Recurse | ForEach-Object {
        Log "  $($_.FullName)"
    }
}

$HtmlReport = "$OutputDir\playwright-report\index.html"
if (Test-Path $HtmlReport) {
    Log "  HTML 报告: $HtmlReport"
}

Log ""
Log "=========================================="
Log "执行完成"
Log "详细日志: $LogFile"
Log "原始输出: $RawOutputFile"
Log "结果文件: $TestResultFile"
Log "=========================================="

# 输出结果摘要（用于 Claude Code 捕获）
Write-Host ""
Write-Host "=== E2E TEST RESULT ==="
Get-Content $TestResultFile
Write-Host "=== END RESULT ==="

exit $ExitCode
