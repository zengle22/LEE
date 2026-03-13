#!/usr/bin/env python
"""
Git Pre-push Hook - L3 Template Lint

在 git push 时自动检查 L3 模板是否符合规范，防止不合规的代码推送。

安装:
    python scripts/install-git-hooks.py

用法（手动）:
    python scripts/git-pre-push-hook.py
"""

import sys
import subprocess
from pathlib import Path

# 导入 lint 脚本
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from lint_l3_templates import lint_templates
except ImportError as e:
    print(f"⚠️  无法导入 lint 模块：{e}")
    print("   请确保在仓库根目录运行，或脚本所在目录可访问")
    sys.exit(0)  # 不阻止 push

try:
    from git_ssot_hook_checks import is_ssot_related_path, collect_release_ids, run_ssot_lint, run_release_checks
except ImportError as e:
    print(f"⚠️  无法导入 SSOT hook 模块：{e}")
    sys.exit(0)


def get_changed_files() -> list[str]:
    """获取所有已修改但未推送的文件列表"""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "@{u}"],
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode != 0:
        # 如果没有上游分支，检查暂存区
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=False
        )
    
    if result.returncode != 0:
        print(f"⚠️  无法获取变更文件列表：{result.stderr}")
        return []
    
    files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    return files


def is_l3_template_related(file_path: str) -> bool:
    """检查文件是否与 L3 模板相关"""
    path = Path(file_path)
    normalized_parts = {part.lower() for part in path.parts}
    is_yaml = path.suffix.lower() in (".yaml", ".yml")
    
    # 检查是否是 L3 模板文件
    if "l3" in file_path.lower() and is_yaml:
        return True
    
    # 仅检查 LEE 规范目录下的 workflow 模板，避免误伤 .github/workflows。
    # 同时排除 L2 模板（包含 l2 或 l2_workflow 路径）
    if (
        is_yaml
        and "workflows" in normalized_parts
        and (
            {"spec-global", "departments"} <= normalized_parts
            or {"spec-global", "core"} <= normalized_parts
        )
        and "l2" not in file_path.lower()
    ):
        return True
    
    # 检查是否是 lint 脚本本身
    if file_path in ('scripts/lint_l3_templates.py', 'scripts/migrate_l3_templates.py'):
        return True
    
    return False


def run_lint_check() -> bool:
    """
    运行 L3 模板 Lint 检查
    
    Returns:
        True 如果检查通过，False 否则
    """
    print("🔍 运行 L3 模板 Lint 检查 (Pre-push Hook)...")
    print()
    
    # 检查是否有变更的 L3 模板相关文件
    changed_files = get_changed_files()
    l3_files = [f for f in changed_files if is_l3_template_related(f)]
    
    if not l3_files:
        print("⚠️  没有 L3 模板相关文件变更，跳过检查")
        return True
    
    print(f"📄 检测到 {len(l3_files)} 个 L3 模板相关文件变更:")
    for f in l3_files:
        print(f"   - {f}")
    print()
    
    # 运行 lint 检查
    from lint_l3_templates import lint_templates
    
    # 只检查变更的文件
    paths_to_check = []
    for f in l3_files:
        path = Path(f)
        if path.exists():
            paths_to_check.append(path)
    
    if not paths_to_check:
        print("⚠️  文件不存在，跳过检查")
        return True
    
    success = lint_templates(paths_to_check, verbose=True)
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ L3 模板 Lint 检查通过")
        print()
        return True
    else:
        print("❌ L3 模板 Lint 检查失败")
        print()
        print("💡 修复建议:")
        print("   1. 使用 'python scripts/migrate_l3_templates.py' 自动迁移")
        print("   2. 确保模板使用 'stages' 字段（不是根级别 'steps'）")
        print("   3. 每个 stage 必须有 'kind: stage'")
        print()
        print("🚫 推送已被阻止。请修复后重新推送。")
        return False


def main():
    """主函数"""
    success = run_lint_check()
    if not success:
        sys.exit(1)

    changed_files = get_changed_files()
    ssot_related = [file_path for file_path in changed_files if is_ssot_related_path(file_path)]
    if ssot_related:
        print("🔍 运行 SSOT lint (Pre-push Hook)...")
        lint_ok, lint_errors = run_ssot_lint(ssot_related)
        if not lint_ok:
            print("❌ SSOT lint 失败")
            for err in lint_errors:
                print(f"   - {err}")
            sys.exit(1)
        print("✅ SSOT lint 通过")

        release_ids = collect_release_ids(ssot_related)
        if release_ids:
            print("🔍 运行 RELEASE gate 检查 (Pre-push Hook)...")
            release_ok, release_errors = run_release_checks(release_ids)
            if not release_ok:
                print("❌ RELEASE gate 检查失败")
                for err in release_errors:
                    print(f"   - {err}")
                sys.exit(1)
            print("✅ RELEASE gate 检查通过")

    sys.exit(0)


if __name__ == "__main__":
    main()
