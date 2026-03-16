@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%scripts\publish-local-to-marathon.ps1"

if not exist "%PS_SCRIPT%" (
  echo publish script not found:
  echo %PS_SCRIPT%
  pause
  exit /b 1
)

echo Publishing local LEE workspace to Marathon runtime...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
  echo Publish failed with exit code %EXIT_CODE%.
  pause
  exit /b %EXIT_CODE%
)

echo Publish completed successfully.
pause
exit /b 0
