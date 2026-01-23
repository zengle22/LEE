@echo off
REM E2E Runner - Windows 快速构建脚本

setlocal

set IMAGE_NAME=e2e-runner:latest
set DOCKER_DIR=%~dp0

echo ============================================
echo E2E Runner - Docker 构建脚本
echo ============================================
echo.

REM 检查 Docker
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] Docker 未安装
    exit /b 1
)

REM 构建镜像
echo [构建] 正在构建 Docker 镜像...
cd /d "%DOCKER_DIR%"
docker build -t %IMAGE_NAME% .

if %ERRORLEVEL% equ 0 (
    echo [成功] 镜像构建成功: %IMAGE_NAME%
) else (
    echo [失败] 镜像构建失败
    exit /b 1
)

REM 验证镜像
echo.
echo [验证] 验证镜像...
docker run --rm %IMAGE_NAME% node --version
docker run --rm %IMAGE_NAME% npx playwright --version

echo.
echo ============================================
echo 所有检查通过！
echo ============================================
echo.
echo 使用方法:
echo   docker run --rm ^
echo     -e BASE_URL="https://test.example.com" ^
echo     -v "%CD%:/work" -w /work ^
echo     %IMAGE_NAME% ^
echo     npx playwright test
echo.

endlocal
