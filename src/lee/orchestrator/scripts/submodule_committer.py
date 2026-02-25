"""
Submodule Committer Script

直接处理 submodule 的提交，不依赖 LLM agent。
"""

import subprocess
import os
import sys
from pathlib import Path
import json
import re


def run_git(cwd, *args):
    """执行 git 命令"""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60
    )
    return result


def get_submodules(root_path):
    """获取所有 submodule"""
    # 使用 git submodule foreach 获取所有 submodule 路径
    result = run_git(root_path, "submodule", "foreach", "--quiet", "echo $name")
    submodules = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line and line != '$name':
            submodules.append(line)
    return submodules


def has_changes(repo_path):
    """检查仓库是否有未提交的更改"""
    result = run_git(repo_path, "status", "--porcelain")
    return bool(result.stdout.strip())


def commit_submodule(submodule_path, main_repo_path):
    """提交 submodule"""
    print(f"\n=== Processing submodule: {submodule_path} ===")

    full_path = os.path.join(main_repo_path, submodule_path)

    # 检查是否有更改
    if not has_changes(full_path):
        print(f"  No changes in {submodule_path}")
        return None

    # 获取更改的文件
    result = run_git(full_path, "status", "--porcelain")
    files = [line[3:] for line in result.stdout.strip().split("\n") if line]
    print(f"  Changed files: {len(files)}")

    # 添加所有文件
    run_git(full_path, "add", "-A")

    # 生成提交信息
    commit_msg = f"chore({submodule_path}): update submodule changes\n\nAuto-committed via workspace-cleanup workflow."

    # 提交
    result = run_git(full_path, "commit", "-m", commit_msg)
    if result.returncode != 0:
        print(f"  Error: {result.stderr}")
        return None

    # 获取提交 hash
    result = run_git(full_path, "rev-parse", "HEAD")
    commit_hash = result.stdout.strip()[:8]
    print(f"  Committed: {commit_hash}")

    return commit_hash


def update_main_repo(main_repo_path):
    """更新主仓库的 submodule 引用"""
    print(f"\n=== Updating main repo: {main_repo_path} ===")

    # 检查是否有更改
    if not has_changes(main_repo_path):
        print("  No changes in main repo")
        return None

    # 添加 submodule 更改
    run_git(main_repo_path, "add", "-A")

    # 生成提交信息
    commit_msg = "chore(submodule): update submodules to latest commits\n\nAuto-committed via workspace-cleanup workflow."

    # 提交
    result = run_git(main_repo_path, "commit", "-m", commit_msg)
    if result.returncode != 0:
        print(f"  Error: {result.stderr}")
        return None

    # 获取提交 hash
    result = run_git(main_repo_path, "rev-parse", "HEAD")
    commit_hash = result.stdout.strip()[:8]
    print(f"  Committed: {commit_hash}")

    return commit_hash


def main():
    main_repo = os.getcwd()
    print(f"Main repository: {main_repo}")

    # 获取所有 submodule
    submodules = get_submodules(main_repo)
    print(f"Found {len(submodules)} submodules: {submodules}")

    if not submodules:
        print("No submodules found")
        return

    commits = []

    # 先处理每个 submodule
    for sm in submodules:
        commit_hash = commit_submodule(sm, main_repo)
        if commit_hash:
            commits.append({"repo": sm, "hash": commit_hash, "type": "submodule"})

    # 然后更新主仓库
    main_commit = update_main_repo(main_repo)
    if main_commit:
        commits.append({"repo": ".", "hash": main_commit, "type": "main"})

    # 输出结果
    print("\n=== Summary ===")
    for c in commits:
        print(f"  {c['repo']}: {c['hash']}")

    # 保存结果到文件
    result = {
        "success": True,
        "commits": commits,
        "total": len(commits)
    }

    output_path = os.path.join(main_repo, ".workflow/workspace-cleanup/submodule-commit-result.yaml")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResult saved to: {output_path}")


if __name__ == "__main__":
    main()
