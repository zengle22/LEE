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


# ============================================================================
# SSOT v1.3 新增命令
# ============================================================================

from lee.orchestrator.execution.artifacts import SSOTType
from lee.orchestrator.execution.artifacts.ssot_service import SSOTValidator


@ssot.command("id-parse")
@click.argument("artifact_id")
def parse_id(artifact_id: str):
    """解析 SSOT ID 结构"""
    from lee.orchestrator.execution.artifacts.id_parser import parse_id as do_parse_id

    result = do_parse_id(artifact_id)

    if result.is_valid:
        click.echo(f"✅ Valid SSOT ID: {artifact_id}")
        click.echo(f"   Prefix: {result.prefix}")
        if result.parent_scope:
            click.echo(f"   Parent Scope: {result.parent_scope}")
        if result.sequence:
            click.echo(f"   Sequence: {result.sequence}")
        if result.suffix:
            click.echo(f"   Suffix: {result.suffix}")
    else:
        click.echo(f"❌ Invalid SSOT ID: {artifact_id}")
        click.echo(f"   Error: {result.error}")


@ssot.command("validate-p0")
@click.argument("artifact_id")
def validate_p0(artifact_id: str):
    """执行 P0 Blocking 校验"""
    manager = ArtifactManager()
    validator = SSOTValidator(manager.registry)

    result = validator.validate_p0(artifact_id)

    if result.is_valid:
        click.echo(f"✅ P0 validation passed for {artifact_id}")
    else:
        click.echo(f"❌ P0 validation failed for {artifact_id}:")
        for err in result.errors:
            click.echo(f"   - {err}")
        raise click.Abort()


@ssot.command("validate-p1")
@click.argument("artifact_id")
def validate_p1(artifact_id: str):
    """执行 P1 Warning 校验"""
    manager = ArtifactManager()
    validator = SSOTValidator(manager.registry)

    result = validator.validate_p1(artifact_id)

    if not result.has_warnings:
        click.echo(f"✅ P1 validation passed for {artifact_id} (no warnings)")
    else:
        click.echo(f"⚠️  P1 warnings for {artifact_id}:")
        for warn in result.warnings:
            click.echo(f"   - {warn}")


@ssot.command("list-ssot")
@click.option("--type", "ssot_type", help="按类型过滤 (src, epic, feat, ui, tech, task, testset, tc, bug, report, adr, evi)")
@click.option("--parent", "parent_id", help="按父对象过滤")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json"]),
              help="输出格式")
def list_ssot(ssot_type: Optional[str], parent_id: Optional[str], output_format: str):
    """列出 SSOT 对象"""
    manager = ArtifactManager()

    artifacts = manager.registry.get_ssot_artifacts()

    # 过滤
    if ssot_type:
        artifacts = [a for a in artifacts if a.properties.get("ssot_type") == ssot_type]
    if parent_id:
        artifacts = [a for a in artifacts if a.properties.get("parent_id") == parent_id]

    if not artifacts:
        click.echo("No SSOT objects found.")
        return

    if output_format == "json":
        data = [
            {
                "id": a.id,
                "type": a.properties.get("ssot_type"),
                "title": a.title,
                "status": a.status.value,
                "parent_id": a.properties.get("parent_id"),
            }
            for a in artifacts
        ]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(f"SSOT Objects ({len(artifacts)}):")
        click.echo("")
        for a in artifacts:
            ssot_type = a.properties.get("ssot_type", "?")
            parent = a.properties.get("parent_id", "-")
            click.echo(f"  [{ssot_type}] {a.id} - {a.title} (parent: {parent})")


# 注册命令到主 CLI
def register_commands(cli_group):
    """将命令注册到 CLI 组"""
    cli_group.add_command(ssot)
