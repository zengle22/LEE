"""
LEE CLI — lee repo 命令

提供 Repo 管理的 CLI 命令：
- lee repo init     自动发现项目中的 git repo 并写入 registry
- lee repo show     查看当前 repo 注册表（YAML 原文）
- lee repo list     列出所有注册的 repo（结构化展示）
- lee repo status   查看各 repo 的实时状态
- lee repo validate 校验所有 repo 的路径和 git root
"""

from __future__ import annotations

import os
import subprocess

import click


# ── Registry 路径常量 ─────────────────────────────────────────────

_DEFAULT_REGISTRY_PATH = os.path.join(".lee", "repo-registry.yaml")


def _find_registry_path(project_root: str) -> str | None:
    """查找已有的 registry 文件"""
    registry_path = os.getenv("LEE_REPO_REGISTRY")
    if registry_path and os.path.exists(registry_path):
        return registry_path

    candidates = [
        os.path.join(project_root, ".lee", "repo-registry.yaml"),
        os.path.join(project_root, "config", "repo-registry.yaml"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def _load_registry(project_root: str):
    """加载 RepoRegistry"""
    from lee.runtime.repo_registry import RepoRegistry

    registry_path = _find_registry_path(project_root)

    if registry_path:
        return RepoRegistry.from_yaml(registry_path, workspace_root=project_root)
    else:
        click.echo(click.style(
            "⚠  No repo registry found. "
            "Run 'lee repo init' to auto-discover repos.",
            fg="yellow"
        ))
        return RepoRegistry(workspace_root=project_root)


# ── Repo 自动发现 ─────────────────────────────────────────────────


def _discover_git_repos(
    project_root: str,
    scan_dirs: list[str],
    max_depth: int = 3,
) -> list[dict]:
    """
    递归扫描目录，发现所有 git 仓库

    Returns:
        [{repo_id, abs_path, rel_path, branch, remote_url}, ...]
    """
    discovered = []
    visited = set()

    for scan_dir in scan_dirs:
        abs_scan = os.path.join(project_root, scan_dir) if not os.path.isabs(scan_dir) else scan_dir
        if not os.path.isdir(abs_scan):
            continue
        _walk_for_git(project_root, abs_scan, discovered, visited, depth=0, max_depth=max_depth)

    # 也检查项目根目录本身
    root_git = os.path.join(project_root, ".git")
    if os.path.exists(root_git) and project_root not in visited:
        info = _extract_repo_info(project_root, project_root)
        if info:
            discovered.insert(0, info)

    return discovered


def _walk_for_git(
    project_root: str,
    current_dir: str,
    results: list,
    visited: set,
    depth: int,
    max_depth: int,
):
    """递归查找 .git 目录"""
    if depth > max_depth:
        return

    real_dir = os.path.realpath(current_dir)
    if real_dir in visited:
        return
    visited.add(real_dir)

    try:
        entries = sorted(os.listdir(current_dir))
    except PermissionError:
        return

    # 当前目录是 git repo？
    if ".git" in entries:
        info = _extract_repo_info(project_root, current_dir)
        if info:
            results.append(info)
        return  # 不递归进入 git repo 内部

    # 继续递归子目录
    for entry in entries:
        if entry.startswith(".") or entry in ("node_modules", "vendor", "__pycache__", "venv", ".venv"):
            continue
        child = os.path.join(current_dir, entry)
        if os.path.isdir(child) and not os.path.islink(child):
            _walk_for_git(project_root, child, results, visited, depth + 1, max_depth)


def _extract_repo_info(project_root: str, repo_dir: str) -> dict | None:
    """从 git repo 提取元信息"""
    try:
        # 获取当前分支
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True, timeout=5,
        )
        default_branch = branch.stdout.strip() if branch.returncode == 0 else "main"

        # 获取 remote url
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_dir, capture_output=True, text=True, timeout=5,
        )
        remote_url = remote.stdout.strip() if remote.returncode == 0 else ""

        # 计算相对路径
        abs_path = os.path.abspath(repo_dir)
        try:
            rel_path = "./" + os.path.relpath(abs_path, project_root)
        except ValueError:
            rel_path = abs_path

        # 推断 repo_id：用最后一级目录名，如果是根目录用 "root"
        if abs_path == os.path.abspath(project_root):
            repo_id = os.path.basename(abs_path) or "root"
        else:
            repo_id = os.path.basename(abs_path)

        # 规范化 repo_id（小写、横线连接）
        repo_id = repo_id.lower().replace(" ", "-").replace("_", "-")

        return {
            "repo_id": repo_id,
            "abs_path": abs_path,
            "rel_path": rel_path,
            "default_branch": default_branch,
            "remote_url": remote_url,
        }
    except Exception:
        return None


def _infer_tags(repo_id: str, rel_path: str) -> list[str]:
    """根据 repo_id 和路径推断 tags"""
    tags = []
    parts = (repo_id + " " + rel_path).lower()

    tag_keywords = {
        "backend": ["backend", "server", "api", "service"],
        "frontend": ["frontend", "web", "app", "ui", "uniapp"],
        "docs": ["docs", "doc", "documentation"],
        "ops": ["ops", "devops", "infra", "deploy", "ci"],
        "proto": ["proto", "contract", "schema", "api-spec"],
        "test": ["test", "qa", "e2e"],
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in parts for kw in keywords):
            tags.append(tag)

    return tags


# ── Click Commands ────────────────────────────────────────────────


@click.group()
def repo():
    """Repo 管理"""
    pass


@repo.command("init")
@click.option("--project-root", default=".", help="项目根目录")
@click.option("--scan-dir", "-d", multiple=True, help="额外扫描目录（相对于项目根）")
@click.option("--max-depth", default=3, help="最大扫描深度")
@click.option("--output", "-o", default=None, help="输出文件路径（默认 .lee/repo-registry.yaml）")
@click.option("--dry-run", is_flag=True, help="仅展示发现结果，不写入文件")
def repo_init(project_root, scan_dir, max_depth, output, dry_run):
    """自动发现 git 仓库并生成/更新 repo registry"""
    import yaml

    project_root = os.path.abspath(project_root)

    # 默认扫描目录
    default_scan_dirs = [".", "repos", "packages", "services", "apps", "libs"]
    all_scan_dirs = list(scan_dir) + default_scan_dirs

    click.echo(f"\n{'─' * 60}")
    click.echo(f"  Repo Discovery — {project_root}")
    click.echo(f"{'─' * 60}\n")
    click.echo(f"  Scanning directories: {', '.join(all_scan_dirs)}")
    click.echo(f"  Max depth: {max_depth}\n")

    # 发现 repos
    discovered = _discover_git_repos(project_root, all_scan_dirs, max_depth)

    if not discovered:
        click.echo(click.style("  No git repositories found.", fg="yellow"))
        return

    click.echo(f"  Found {click.style(str(len(discovered)), fg='green', bold=True)} git repo(s):\n")
    for d in discovered:
        click.echo(f"    {click.style(d['repo_id'], fg='cyan', bold=True)}")
        click.echo(f"      Path:   {d['rel_path']}")
        click.echo(f"      Branch: {d['default_branch']}")
        if d.get("remote_url"):
            click.echo(f"      Remote: {d['remote_url']}")
        click.echo()

    if dry_run:
        click.echo(click.style("  [dry-run] No files written.", fg="yellow"))
        return

    # 确定输出路径
    output_path = output or os.path.join(project_root, _DEFAULT_REGISTRY_PATH)
    output_path = os.path.abspath(output_path)

    # 加载已有 registry（如存在则合并）
    existing_repos = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_data = yaml.safe_load(f) or {}
            existing_repos = existing_data.get("repos", {})
            click.echo(f"  Merging with existing registry: {len(existing_repos)} existing repo(s)")
        except Exception:
            pass

    # 构建 registry 数据
    repos_data = dict(existing_repos)  # 保留已有条目
    new_count = 0

    for d in discovered:
        rid = d["repo_id"]
        if rid in repos_data:
            click.echo(f"    {click.style('skip', fg='yellow')}  {rid} (already registered)")
            continue

        tags = _infer_tags(rid, d["rel_path"])
        entry = {
            "path": d["rel_path"],
            "type": "git",
            "default_branch": d["default_branch"],
        }
        if d.get("remote_url"):
            entry["url"] = d["remote_url"]
        if tags:
            entry["tags"] = tags

        repos_data[rid] = entry
        new_count += 1
        click.echo(f"    {click.style('add', fg='green', bold=True)}   {rid}")

    # 写入文件
    registry_data = {
        "version": "1.0",
        "repos": repos_data,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            registry_data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    click.echo()
    click.echo(click.style(
        f"  ✓ Registry written: {output_path}",
        fg="green", bold=True,
    ))
    click.echo(f"    Total: {len(repos_data)} repo(s) ({new_count} new, {len(existing_repos)} existing)")
    click.echo()
    click.echo(f"  Next steps:")
    click.echo(f"    • Review:   {click.style('lee repo show', bold=True)}")
    click.echo(f"    • Status:   {click.style('lee repo status', bold=True)}")
    click.echo(f"    • Validate: {click.style('lee repo validate', bold=True)}")
    click.echo()


@repo.command("show")
@click.option("--project-root", default=".", help="项目根目录")
def repo_show(project_root):
    """查看当前 repo 注册表（YAML 原文）"""
    project_root = os.path.abspath(project_root)
    registry_path = _find_registry_path(project_root)

    if not registry_path:
        click.echo(click.style(
            "⚠  No repo registry found.\n"
            "   Run 'lee repo init' to auto-discover and create one.",
            fg="yellow",
        ))
        return

    click.echo(f"\n{'─' * 60}")
    click.echo(f"  Registry: {click.style(registry_path, fg='cyan')}")
    click.echo(f"{'─' * 60}\n")

    with open(registry_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 简单语法高亮
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            click.echo(click.style(line, fg="bright_black"))
        elif stripped.startswith("- "):
            click.echo(click.style(line, fg="white"))
        elif ":" in line:
            key, _, val = line.partition(":")
            click.echo(
                click.style(key + ":", fg="cyan")
                + click.style(val, fg="white")
            )
        else:
            click.echo(line)

    click.echo()


@repo.command("list")
@click.option("--project-root", default=".", help="项目根目录")
@click.option("--tag", multiple=True, help="按 tag 过滤")
def repo_list(project_root, tag):
    """列出所有注册的 Repo（结构化展示）"""
    project_root = os.path.abspath(project_root)
    registry = _load_registry(project_root)

    repos = registry.list_repos()
    if not repos:
        click.echo("No repos registered.")
        return

    # 按 tag 过滤
    if tag:
        tag_set = set(tag)
        repos = [r for r in repos if tag_set.intersection(r.tags)]

    click.echo(f"\n{'─' * 60}")
    click.echo(f"  Repo Registry  ({len(repos)} repos)")
    click.echo(f"{'─' * 60}\n")

    for r in sorted(repos, key=lambda x: x.repo_id):
        tags_str = ", ".join(r.tags) if r.tags else "-"
        policy_str = ", ".join(r.path_policy[:3]) if r.path_policy else "(unrestricted)"
        if len(r.path_policy) > 3:
            policy_str += f" (+{len(r.path_policy) - 3} more)"

        click.echo(f"  {click.style(r.repo_id, fg='cyan', bold=True)}")
        click.echo(f"    Path:     {r.path}")
        click.echo(f"    Type:     {r.type}  |  Branch: {r.default_branch}")
        click.echo(f"    Tags:     {tags_str}")
        click.echo(f"    Policy:   {policy_str}")
        if r.description:
            click.echo(f"    Desc:     {r.description}")
        if r.owner:
            click.echo(f"    Owner:    {r.owner}")
        click.echo()


@repo.command("status")
@click.option("--project-root", default=".", help="项目根目录")
@click.argument("repo_id", required=False)
def repo_status(project_root, repo_id):
    """查看 Repo 实时状态"""
    project_root = os.path.abspath(project_root)
    registry = _load_registry(project_root)

    if repo_id:
        # 单个 repo
        try:
            st = registry.get_status(repo_id)
        except ValueError as e:
            click.echo(click.style(f"✗ {e}", fg="red"))
            raise SystemExit(1)
        _print_status(st)
    else:
        # 所有 repo
        statuses = registry.get_all_status()
        if not statuses:
            click.echo("No repos registered.")
            return

        click.echo(f"\n{'─' * 60}")
        click.echo(f"  Repo Status")
        click.echo(f"{'─' * 60}\n")

        for st in statuses:
            _print_status(st)


@repo.command("validate")
@click.option("--project-root", default=".", help="项目根目录")
def repo_validate(project_root):
    """校验所有 Repo 的路径和 git root"""
    project_root = os.path.abspath(project_root)
    registry = _load_registry(project_root)

    errors = registry.validate()

    if not errors:
        click.echo(click.style(
            f"✓ All {len(registry)} repos validated successfully",
            fg="green", bold=True,
        ))
    else:
        click.echo(click.style(
            f"✗ Validation failed ({len(errors)} error(s)):",
            fg="red", bold=True,
        ))
        for err in errors:
            click.echo(f"  • {err}")
        raise SystemExit(1)


def _print_status(st):
    """格式化打印 RepoStatus"""
    if st.error:
        icon = click.style("✗", fg="red")
        status = click.style(st.error, fg="red")
    elif not st.exists:
        icon = click.style("?", fg="yellow")
        status = click.style("not found", fg="yellow")
    elif st.is_clean:
        icon = click.style("✓", fg="green")
        status = click.style("clean", fg="green")
    else:
        icon = click.style("~", fg="yellow")
        status = click.style(f"{st.uncommitted_changes} uncommitted", fg="yellow")

    click.echo(f"  {icon} {click.style(st.repo_id, fg='cyan', bold=True)}")
    if st.abs_path:
        click.echo(f"    Path:     {st.abs_path}")
    if st.current_branch:
        click.echo(f"    Branch:   {st.current_branch} ({st.current_commit})")
    click.echo(f"    Status:   {status}")
    click.echo()

