@echo off
REM 修复 Claude Code 官方登录配置
REM 此脚本会重置 Claude Code 配置，恢复官方登录

echo 正在修复 Claude Code 官方登录配置...
echo.

set CLAUDE_CONFIG=%USERPROFILE%\.claude\settings.json

echo 备份当前配置...
copy "%CLAUDE_CONFIG%" "%CLAUDE_CONFIG%.backup" >nul 2>&1

echo 创建干净的配置文件...
(
echo {
echo   "enabledPlugins": {
echo     "glm-plan-bug@zai-coding-plugins": true,
echo     "glm-plan-usage@zai-coding-plugins": true
echo   },
echo   "permissions": {
echo     "allow": [
echo       "mcp__pencil"
echo     ]
echo   }
echo }
) > "%CLAUDE_CONFIG%"

echo.
echo ========================================
echo 配置已修复！
echo ========================================
echo.
echo 下一步操作：
echo 1. 关闭所有 Claude Code 终端窗口
echo 2. 重新打开终端，运行: claude
echo 3. 浏览器会自动打开官方登录页面
echo.
echo 如果使用 CC Switch 切换中转服务：
echo - 在 CC Switch 中不要使用"官方登录"预设
echo - 直接切换到需要的中转服务供应商即可
echo.
pause
