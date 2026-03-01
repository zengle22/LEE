"""
SSOT CLI Commands - SSOT 真理链管理命令
"""

import json
import yaml
import click
from pathlib import Path
from typing import Optional

from lee.orchestrator.execution.artifacts import ArtifactManager
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService


@click.group()
def ssot():
    """SSOT 真理链管理命令"""
    pass


@ssot.command("build-index")
@click.option("--output", "-o", default=None, help="输出文件路径 (默认：.artifacts/trace/ssot-index.yaml)")
@click.option("--release", help="仅构建指定 release 的索引")
def build_index(output: Optional[str], release: Optional[str]):
    """构建/更新 SSOT 索引缓存"""
    manager = ArtifactManager()

    # 确定输出路径
    if output is None:
        output = Path(manager.root_path) / "trace" / "ssot-index.yaml"
    else:
        output = Path(output)

    # 确保目录存在
    output.parent.mkdir(parents=True, exist_ok=True)

    # 获取所有 artifacts
    all_artifacts = list(manager.registry._artifacts.values())

    # 按 release 过滤
    if release:
        all_artifacts = [a for a in all_artifacts if release in (a.tags or [])]

    # 构建节点
    nodes = []
    for a in all_artifacts:
        nodes.append({
            "id": a.id,
            "type": a.type.value,
            "category": a.category,
            "governance_kind": a.governance_kind.value if a.governance_kind else None,
        })

    # 构建边
    edges = []
    by_id = {a.id: a for a in all_artifacts}

    for a in all_artifacts:
        # derived_from 边
        if a.derived_from:
            edges.append({
                "from": a.id,
                "to": a.derived_from,
                "type": "derived_from",
            })

        # implements 边
        for impl_id in a.implements or []:
            edges.append({
                "from": a.id,
                "to": impl_id,
                "type": "implements",
            })

        # verifies 边
        for ver_id in a.verifies or []:
            edges.append({
                "from": a.id,
                "to": ver_id,
                "type": "verifies",
            })

        # supersedes 边
        if a.supersedes:
            edges.append({
                "from": a.id,
                "to": a.supersedes,
                "type": "supersedes",
            })

    # 生成索引文件
    index_data = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "generated_at": Path(output).stat().st_mtime if Path(output).exists() else None,
            "artifact_count": len(nodes),
            "edge_count": len(edges),
            "release_filter": release,
        },
    }

    # 写入文件
    with open(output, "w", encoding="utf-8") as f:
        yaml.dump(index_data, f, allow_unicode=True, sort_keys=False)

    click.echo(f"✅ SSOT index built: {output}")
    click.echo(f"   Nodes: {len(nodes)}, Edges: {len(edges)}")


@ssot.command("validate")
@click.option("--run-id", help="按 run ID 校验")
@click.option("--release", help="按 release tag 校验")
@click.option("--enforce", is_flag=True, help="强制模式 (不通过则失败)")
def validate_ssot(run_id: Optional[str], release: Optional[str], enforce: bool):
    """校验 SSOT 真理链完整性"""
    manager = ArtifactManager()
    service = SSOTService(manager)

    valid, errors = service.validate(run_id=run_id, release=release)

    if valid:
        click.echo("✅ SSOT validation passed.")
    else:
        click.echo("❌ SSOT validation failed:")
        for err in errors:
            click.echo(f"  - {err}")
        if enforce:
            raise click.Abort()


@ssot.command("impact")
@click.argument("artifact_id")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json"]),
              help="输出格式")
def show_impact(artifact_id: str, output_format: str):
    """分析某个 artifact 的影响范围"""
    manager = ArtifactManager()
    service = SSOTService(manager)

    impact = service.impact(artifact_id)

    if not any(impact.values()):
        click.echo(f"No impact found for {artifact_id}")
        return

    if output_format == "json":
        click.echo(json.dumps(impact, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Impact analysis for {artifact_id}:")
        click.echo("")

        if impact.get("direct_dependents"):
            click.echo("Direct Dependents:")
            for dep_id in impact["direct_dependents"]:
                click.echo(f"  - {dep_id}")
            click.echo("")

        if impact.get("indirect_dependents"):
            click.echo(f"Indirect Dependents ({len(impact['indirect_dependents'])}):")
            for dep_id in impact["indirect_dependents"][:20]:
                click.echo(f"  - {dep_id}")
            if len(impact["indirect_dependents"]) > 20:
                click.echo(f"  ... and {len(impact['indirect_dependents']) - 20} more")
            click.echo("")

        if impact.get("verifiers"):
            click.echo("Verifiers (Tests):")
            for ver_id in impact["verifiers"]:
                click.echo(f"  - {ver_id}")


@ssot.command("show-chain")
@click.argument("artifact_id")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json"]),
              help="输出格式")
def show_chain(artifact_id: str, output_format: str):
    """显示某个 artifact 的真理链路径"""
    manager = ArtifactManager()
    service = SSOTService(manager)

    chain = service.show_chain(artifact_id)

    if not chain:
        click.echo(f"Chain not found for {artifact_id}")
        return

    if output_format == "json":
        click.echo(json.dumps(chain, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Truth chain for {artifact_id}:")
        click.echo("")

        for i, entry in enumerate(chain):
            prefix = "  " * i
            relation = entry.get("relation", "")
            click.echo(f"{prefix}[{i}] {entry['id']} ({entry['category']})")
            if relation:
                click.echo(f"{prefix}    └─ {relation}")


# 注册命令到主 CLI
def register_commands(cli_group):
    """将命令注册到 CLI 组"""
    cli_group.add_command(ssot)
