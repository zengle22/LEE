#!/usr/bin/env python
"""
Git Pre-commit Hook - Hardcoded Path Detector

在 git commit 时自动检测硬编码路径，防止不合规的代码提交。

安装:
    python scripts/install-git-hooks.py

用法（手动）:
    python scripts/git-pre-commit-hook.py
"""

import sys
import subprocess
import importlib.util
from pathlib import Path

# 导入硬编码路径检测器
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
LEGACY_DETECT_SCRIPT = SCRIPT_DIR / "detect-hardcoded-paths.py"
HardcodedPathDetector = None

try:
    from detect_hardcoded_paths import HardcodedPathDetector
except ImportError:
    if LEGACY_DETECT_SCRIPT.exists():
        spec = importlib.util.spec_from_file_location("detect_hardcoded_paths", LEGACY_DETECT_SCRIPT)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            HardcodedPathDetector = getattr(module, "HardcodedPathDetector", None)
        else:
            print("⚠️  无法加载硬编码路径检测模块")
            print("   请确保 scripts/detect-hardcoded-paths.py 可访问")
            sys.exit(0)
    elif not LEGACY_DETECT_SCRIPT.exists():
        print("⚠️  无法导入检测模块：detect_hardcoded_paths")
        print("   请确保在仓库根目录运行，或脚本所在目录可访问")
        sys.exit(0)  # 不阻止 commit

try:
    from git_ssot_hook_checks import is_ssot_related_path, run_ssot_lint
except ImportError as e:
    print(f"⚠️  无法导入 SSOT hook 模块：{e}")
    sys.exit(0)


def get_staged_files() -> list[str]:
    """获取所有暂存的文件列表"""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode != 0:
        print(f"❌ 无法获取暂存文件列表：{result.stderr}")
        return []
    
    files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    return files


def get_staged_content(file_path: str) -> str:
    """获取暂存区文件内容"""
    result = subprocess.run(
        ["git", "show", f":{file_path}"],
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def check_staged_files() -> bool:
    """
    检查所有暂存的文件
    
    Returns:
        True 如果没有发现硬编码路径，False 否则
    """
    print("🔍 运行硬编码路径检测 (Pre-commit Hook)...")
    print()
    
    staged_files = get_staged_files()
    if not staged_files:
        print("⚠️  没有暂存的文件")
        return True
    
    print(f"📄 检测到 {len(staged_files)} 个暂存文件")
    
    # 只检查 Python 和 YAML 文件
    target_extensions = {'.py', '.yaml', '.yml', '.json', '.md'}
    target_files = [
        f for f in staged_files
        if Path(f).suffix.lower() in target_extensions
    ]
    
    if not target_files:
        print("✅ 没有需要检查的文件类型")
        return True
    
    print(f"🔍 将检查 {len(target_files)} 个文件 (.py, .yaml, .yml, .json, .md)")
    print()
    
    if HardcodedPathDetector is None:
        result = subprocess.run(
            [sys.executable, str(LEGACY_DETECT_SCRIPT), "--fail", *target_files],
            check=False,
        )
        return result.returncode == 0

    # 创建检测器
    detector = HardcodedPathDetector()
    
    violations = []
    
    for file_path in target_files:
        content = get_staged_content(file_path)
        if not content:
            continue
        
        # 检测文件内容
        result = detector.check_content(content, file_path)
        
        if result.violations:
            violations.append((file_path, result.violations))
    
    # 报告结果
    print()
    print("=" * 60)
    
    if violations:
        print("❌ 发现硬编码路径违规:")
        print()
        
        for file_path, v_list in violations:
            print(f"📄 {file_path}")
            for v in v_list:
                print(f"   行 {v.line}: {v.snippet}")
                print(f"      建议：{v.suggestion}")
            print()
        
        print("=" * 60)
        print("❌ 硬编码路径检测失败")
        print()
        print("💡 修复建议:")
        print("   1. 使用路径变量（如 {{ artifacts_dir }}）替代硬编码路径")
        print("   2. 如果是工具目录（.artifacts, .workflow），请添加到允许列表")
        print("   3. 参考 docs/guides/path-variables-guide.md")
        print()
        print("🚫 提交已被阻止。请修复后重新提交。")
        return False
    else:
        print("✅ 硬编码路径检测通过")
        print()
        return True


def main():
    """主函数"""
    success = check_staged_files()
    if not success:
        sys.exit(1)

    staged_files = get_staged_files()
    ssot_related = [file_path for file_path in staged_files if is_ssot_related_path(file_path)]
    if ssot_related:
        print("🔍 运行 SSOT lint (Pre-commit Hook)...")
        passed, errors = run_ssot_lint(ssot_related)
        if not passed:
            print("❌ SSOT lint 失败")
            for err in errors:
                print(f"   - {err}")
            sys.exit(1)
        print("✅ SSOT lint 通过")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
