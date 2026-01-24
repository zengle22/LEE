@echo off
REM LEE 环境快速设置脚本 (Windows)

echo ====================================
echo  LEE 环境快速设置
echo ====================================
echo.

REM 1. 复制环境变量模板
if not exist .env (
    echo 创建 .env 文件...
    copy .env.example .env >nul
    echo [32m✅ .env 文件已创建[0m
) else (
    echo [32m✅ .env 文件已存在[0m
)

REM 2. 安装依赖
echo.
echo 安装 Python 依赖...
python scripts\install_requirements.py

REM 3. 设置环境
echo.
echo 设置环境...
python scripts\setup_env.py

REM 4. 运行测试
echo.
echo 运行测试...
python scripts\test_all.py

echo.
echo ====================================
echo  ✅ 设置完成！
echo ====================================
pause
