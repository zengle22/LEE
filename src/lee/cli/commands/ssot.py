"""
SSOT CLI Commands - SSOT 真理链管理命令
"""

import json
import yaml
import click
from pathlib import Path
from typing import Optional

from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTType
from lee.orchestrator.execution.artifacts.chain_testing import (
    ChainTestRunner,
    SampleLibrary,
    write_chain_ci_templates,
)
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService, SSOTValidator
from lee.orchestrator.execution.artifacts.ssot_files import (
    lint_ssot_front_matter,
)


@click.group()
def ssot():
    """SSOT 真理链管理命令"""
    pass


def _parse_status(status: str):
    from lee.orchestrator.execution.artifacts.types import ArtifactStatus

    return ArtifactStatus[status.upper()]


def _parse_derived_from_items(items: tuple[str, ...]) -> list[dict]:
    refs = []
    for item in items:
        parts = item.split(":")
        if len(parts) < 2:
            raise click.ClickException(f"Invalid --derived-from value: {item}. Expected ID:VERSION[:SLICE_KEY]")
        ref = {
            "id": parts[0],
            "version": parts[1],
        }
        if len(parts) >= 3 and parts[2]:
            ref["slice_key"] = parts[2]
        refs.append(ref)
    return refs


def _parse_property_items(items: tuple[str, ...]) -> dict:
    properties = {}
    for item in items:
        if "=" not in item:
            raise click.ClickException(f"Invalid --property value: {item}. Expected KEY=VALUE")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise click.ClickException(f"Invalid --property key in: {item}")
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        properties[key] = value
    return properties


@ssot.command("create")
@click.option(
    "--type",
    "ssot_type",
    required=True,
    type=click.Choice([member.value for member in SSOTType]),
    help="SSOT 对象类型",
)
@click.option("--title", required=True, help="对象标题")
@click.option("--body", default="", help="正文内容")
@click.option("--content-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="正文文件路径")
@click.option("--run-id", default="manual-ssot-create", show_default=True, help="创建来源 run ID")
@click.option("--status", "status_name", default="draft", type=click.Choice(["draft", "active", "frozen", "archived", "deprecated"]), show_default=True, help="对象状态")
@click.option("--version", default="v1", show_default=True, help="对象版本")
@click.option("--parent-id", help="父对象 ID")
@click.option("--owner", help="负责人")
@click.option("--tag", "tags", multiple=True, help="标签，可重复")
@click.option("--source-ref", "source_refs", multiple=True, help="源引用，可重复")
@click.option("--related-id", "related_ids", multiple=True, help="横向关联 ID，可重复")
@click.option("--implements", "implements_ids", multiple=True, help="实现对象 ID，可重复")
@click.option("--verifies", "verifies_ids", multiple=True, help="验证对象 ID，可重复")
@click.option("--derived-from", "derived_from_items", multiple=True, help="格式 ID:VERSION[:SLICE_KEY]，可重复")
@click.option("--property", "property_items", multiple=True, help="扩展属性，格式 KEY=VALUE，可重复；VALUE 支持 JSON")
@click.option("--release-version", help="RELEASE 类型必填，格式如 1.4.0")
@click.option("--report-kind", help="REPORT 类型可选，用于 release 级报告 ID")
def create_ssot_object(
    ssot_type: str,
    title: str,
    body: str,
    content_file: Optional[Path],
    run_id: str,
    status_name: str,
    version: str,
    parent_id: Optional[str],
    owner: Optional[str],
    tags: tuple[str, ...],
    source_refs: tuple[str, ...],
    related_ids: tuple[str, ...],
    implements_ids: tuple[str, ...],
    verifies_ids: tuple[str, ...],
    derived_from_items: tuple[str, ...],
    property_items: tuple[str, ...],
    release_version: Optional[str],
    report_kind: Optional[str],
):
    """创建正式 SSOT 对象。"""
    manager = ArtifactManager()
    content = content_file.read_text(encoding="utf-8") if content_file else body
    properties = _parse_property_items(property_items)
    if release_version:
        properties["release_version"] = release_version
    if report_kind:
        properties["report_kind"] = report_kind
    object_type = SSOTType(ssot_type)
    if object_type == SSOTType.RELEASE and not properties.get("release_version"):
        raise click.ClickException("--release-version is required when --type release")
    if object_type == SSOTType.REPORT and parent_id and parent_id.startswith("REL-") and not properties.get("report_kind"):
        raise click.ClickException("--report-kind is required for release-level report objects")
    derived_from = _parse_derived_from_items(derived_from_items)
    try:
        artifact = manager.create_ssot(
            ssot_type=object_type,
            title=title,
            content=content,
            run_id=run_id,
            parent_id=parent_id,
            derived_from=derived_from,
            source_refs=list(source_refs),
            related_ids=list(related_ids),
            verifies=list(verifies_ids),
            implements=list(implements_ids),
            owner=owner,
            tags=list(tags),
            status=_parse_status(status_name),
            version=version,
            properties=properties,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"✅ created {artifact.id}")
    click.echo(f"   path: {artifact.path}")


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
        properties = a.properties or {}
        nodes.append({
            "id": a.id,
            "type": a.type.value,
            "category": a.category,
            "governance_kind": a.governance_kind.value if a.governance_kind else None,
            "ssot_type": properties.get("ssot_type"),
            "parent_id": properties.get("parent_id"),
            "slice_keys": [item.get("slice_key") for item in properties.get("slices", []) if isinstance(item, dict)],
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

        for ref in (a.properties or {}).get("derived_from_ids", []):
            if isinstance(ref, dict) and ref.get("id"):
                edges.append({
                    "from": a.id,
                    "to": ref["id"],
                    "type": "derived_from_ids",
                    "version": ref.get("version"),
                    "slice_key": ref.get("slice_key"),
                })
            elif isinstance(ref, str):
                edges.append({
                    "from": a.id,
                    "to": ref,
                    "type": "derived_from_ids",
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


@ssot.command("rebuild-registry")
def rebuild_registry():
    """从正式 SSOT 文件全量重建 registry。"""
    manager = ArtifactManager()
    count = manager.rebuild_ssot_registry()
    click.echo(f"✅ registry rebuilt from SSOT files: {count} artifacts")


@ssot.command("sync")
def sync_registry():
    """同步正式 SSOT 文件到 registry。"""
    manager = ArtifactManager()
    count = manager.sync_ssot_registry()
    click.echo(f"✅ registry synced from SSOT files: {count} artifacts")


@ssot.command("formalize")
@click.option("--id", "artifact_ids", multiple=True, required=True, help="待定版的 SSOT ID，可重复")
def formalize_ssot(artifact_ids: tuple[str, ...]):
    """内部命令：批量定版 SSOT ID 并重写引用。"""
    manager = ArtifactManager()
    service = SSOTService(manager)

    try:
        result = service.formalize(list(artifact_ids))
    except (ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"✅ formalized {result['count']} artifacts")
    for old_id, new_id in result["replacements"].items():
        click.echo(f"   {old_id} -> {new_id}")


@ssot.command("lint")
@click.option("--changed-only", is_flag=True, help="保留接口，当前仍执行全量扫描")
def lint_ssot(changed_only: bool):
    """扫描正式 SSOT 文件并做基础 front matter/lint 校验。"""
    del changed_only
    manager = ArtifactManager()
    manager.rebuild_ssot_registry()

    errors = lint_ssot_front_matter(manager.project_root)

    validator = SSOTValidator(manager.registry)
    for artifact in manager.registry.get_ssot_artifacts():
        result = validator.validate_p0(artifact.id)
        errors.extend(f"{artifact.id}: {err}" for err in result.errors)

    if errors:
        click.echo("❌ SSOT lint failed:")
        for err in errors:
            click.echo(f"  - {err}")
        raise click.Abort()

    click.echo("✅ SSOT lint passed")


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


@ssot.command("release-check")
@click.argument("release_id")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json"]),
              help="输出格式")
@click.option("--enforce", is_flag=True, help="强制模式 (不通过则失败)")
def release_check(release_id: str, output_format: str, enforce: bool):
    """执行 release 聚合校验。"""
    manager = ArtifactManager()
    service = SSOTService(manager)
    result = service.release_check(release_id)

    if output_format == "json":
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        marker = "✅" if result["passed"] else "❌"
        click.echo(f"{marker} Release check for {release_id}")
        for err in result.get("errors", []):
            click.echo(f"  - ERROR: {err}")
        for warn in result.get("warnings", []):
            click.echo(f"  - WARN: {warn}")
        if result.get("devplans"):
            click.echo(f"  Devplans: {', '.join(result['devplans'])}")
        if result.get("testplans"):
            click.echo(f"  Testplans: {', '.join(result['testplans'])}")

    if enforce and not result["passed"]:
        raise click.Abort()


@ssot.command("plan-check")
@click.argument("plan_id")
@click.option("--commit", "commit_plan", is_flag=True, help="通过校验后将计划视为 committed")
def plan_check(plan_id: str, commit_plan: bool):
    """校验 DEVPLAN/TESTPLAN 的基础结构。"""
    manager = ArtifactManager()
    artifact = manager.get(plan_id)
    if not artifact:
        raise click.ClickException(f"Plan not found: {plan_id}")

    validator = SSOTValidator(manager.registry)
    result = validator.validate_p0(plan_id)
    if result.errors:
        for err in result.errors:
            click.echo(f"  - {err}")
        raise click.Abort()

    if commit_plan:
        click.echo(f"✅ {plan_id} passed and is ready for committed transition")
    else:
        click.echo(f"✅ {plan_id} passed")


@ssot.command("plan-derive")
@click.argument("release_id")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json"]),
              help="输出格式")
def plan_derive(release_id: str, output_format: str):
    """从 RELEASE scope 派生 DEVPLAN/TESTPLAN 骨架。"""
    manager = ArtifactManager()
    service = SSOTService(manager)
    result = service.derive_plans(release_id)

    if output_format == "json":
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        click.echo(f"✅ plans derived for {release_id}")
        for key, value in result.items():
            click.echo(f"  - {key}: {value}")


@ssot.command("render-view")
@click.argument("view_name")
@click.option("--release-id", required=True, help="关联的 RELEASE ID")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json"]),
              help="输出格式")
def render_view(view_name: str, release_id: str, output_format: str):
    """渲染派生视图。"""
    manager = ArtifactManager()
    service = SSOTService(manager)
    result = service.render_view(view_name, release_id=release_id)

    if output_format == "json":
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return

    click.echo(f"View: {result['view']}")
    click.echo(f"Release: {result['release_id']}")

    if view_name == "release-dashboard":
        click.echo(f"Status: {result['status']}")
        click.echo(f"Scope size: {result['release_scope_size']}")
        click.echo(f"Gate passed: {result['gate_passed']}")
        for err in result.get("gate_errors", []):
            click.echo(f"  - ERROR: {err}")
        for warn in result.get("gate_warnings", []):
            click.echo(f"  - WARN: {warn}")
        return

    if view_name == "feat-delivery-matrix":
        for row in result.get("features", []):
            click.echo(
                f"{row['feat_id']}@{row['version']} "
                f"dev={row['covered_by_devplan']} test={row['covered_by_testplan']} "
                f"reports={len(row['test_reports'])}"
            )
        return

    for row in result.get("coverage", []):
        click.echo(
            f"{row['feat_id']} slice={row['slice_key']} "
            f"covered={row['covered_by_testplan']} "
            f"reports={row['test_report_count']}"
        )


@ssot.command("release-close")
@click.argument("release_id")
def release_close(release_id: str):
    """对 release 执行关闭前检查。"""
    manager = ArtifactManager()
    service = SSOTService(manager)
    result = service.release_check(release_id)
    if not result["passed"]:
        for err in result["errors"]:
            click.echo(f"  - {err}")
        raise click.Abort()
    click.echo(f"✅ {release_id} passed close gate")


@ssot.command("release-cut")
@click.argument("release_version")
@click.option("--title", required=True, help="Release 标题")
@click.option("--feat", "feat_refs", multiple=True, help="格式 FEAT-001:v1")
def release_cut(release_version: str, title: str, feat_refs: tuple[str, ...]):
    """创建 release scope 骨架。"""
    manager = ArtifactManager()
    derived_from_ids = []
    for item in feat_refs:
        feat_id, version = item.split(":", 1)
        derived_from_ids.append({"id": feat_id, "version": version, "required": True})

    artifact = manager.create_ssot(
        ssot_type=SSOTType.RELEASE,
        title=title,
        content=f"# {title}\n",
        run_id="manual-release-cut",
        derived_from=derived_from_ids,
        properties={"release_version": release_version},
    )
    click.echo(f"✅ created {artifact.id}")


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


@ssot.command("chain-test")
@click.option("--project-root", type=click.Path(file_okay=False, path_type=Path), default=Path.cwd(), show_default=True, help="项目根目录")
@click.option("--output-dir", type=click.Path(file_okay=False, path_type=Path), default=None, help="报告输出目录，默认写入 .artifacts/trace/chain-tests")
@click.option("--tester", "tester_ids", multiple=True, type=click.Choice(["schema", "trace", "semantic", "overlap", "replay", "executable"]), help="指定测试器，可重复")
@click.option("--sample-strategy", type=click.Choice(["all", "random", "importance", "stratified"]), default="all", show_default=True, help="采样策略")
@click.option("--sample-size", type=int, default=None, help="采样数量")
@click.option("--seed", type=int, default=7, show_default=True, help="随机种子")
@click.option("--use-cache/--no-cache", default=True, show_default=True, help="是否启用测试结果缓存")
@click.option("--incremental/--no-incremental", default=False, show_default=True, help="是否按快照执行增量测试")
@click.option("--baseline-path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="增量测试基线快照路径")
@click.option("--fail-under", type=float, default=None, help="overall 通过率阈值，低于该值返回非零退出码")
def chain_test(
    project_root: Path,
    output_dir: Optional[Path],
    tester_ids: tuple[str, ...],
    sample_strategy: str,
    sample_size: Optional[int],
    seed: int,
    use_cache: bool,
    incremental: bool,
    baseline_path: Optional[Path],
    fail_under: Optional[float],
):
    """运行需求链一致性测试并输出 report.json / scorecard.md。"""
    project_root = project_root.resolve()
    manager = ArtifactManager(project_root=project_root, root_path=project_root / ".artifacts")
    runner = ChainTestRunner(manager).register_defaults()
    report = runner.run(
        tester_ids=list(tester_ids) or None,
        sample_strategy=sample_strategy,
        sample_size=sample_size,
        seed=seed,
        use_cache=use_cache,
        incremental=incremental,
        baseline_path=baseline_path,
    )
    target_dir = output_dir or (manager.root_path / "trace" / "chain-tests")
    written = runner.write_report(report, target_dir)
    click.echo(f"Chain tests completed: {'PASS' if report.metrics.get('overall_passed') else 'FAIL'}")
    click.echo(f"report.json: {written['report_json']}")
    click.echo(f"scorecard.md: {written['scorecard_md']}")
    if fail_under is not None:
        pass_rate = (
            (report.metrics.get("passed_tester_count", 0) / max(report.metrics.get("tester_count", 1), 1))
            * 100
        )
        if pass_rate < fail_under:
            raise click.ClickException(f"overall tester pass rate {pass_rate:.2f} is below fail-under {fail_under:.2f}")


@ssot.command("chain-init-samples")
@click.option("--project-root", type=click.Path(file_okay=False, path_type=Path), default=Path.cwd(), show_default=True, help="项目根目录")
@click.option("--output-dir", type=click.Path(file_okay=False, path_type=Path), default=None, help="样本目录，默认 tests/fixtures/chain_testing")
@click.option("--version", "sample_version", default="v1", show_default=True, help="样本版本号")
def chain_init_samples(project_root: Path, output_dir: Optional[Path], sample_version: str):
    """初始化黄金样本集目录与默认样本。"""
    project_root = project_root.resolve()
    root_dir = output_dir or (project_root / "tests" / "fixtures" / "chain_testing")
    library = SampleLibrary(root_dir)
    counts = library.initialize_defaults(version=sample_version)
    click.echo(f"Initialized chain samples at {root_dir}")
    click.echo(f"  active_version: {library.active_version()}")
    for category, count in counts.items():
        click.echo(f"  {category}: {count}")


@ssot.command("chain-install-ci")
@click.option("--project-root", type=click.Path(file_okay=False, path_type=Path), default=Path.cwd(), show_default=True, help="项目根目录")
def chain_install_ci(project_root: Path):
    """生成 requirement chain CI/CD 模板。"""
    written = write_chain_ci_templates(project_root.resolve())
    click.echo(f"github workflow: {written['github_workflow']}")
    click.echo(f"gitlab ci: {written['gitlab_ci']}")
    click.echo(f"dockerfile: {written['dockerfile']}")


# 注册命令到主 CLI
def register_commands(cli_group):
    """将命令注册到 CLI 组"""
    cli_group.add_command(ssot)
