"""
QA SUT (System Under Test) configuration commands

提供 SUT 环境配置的管理命令。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
import yaml

from lee.qa.runner.sut import (
    SUTConfig,
    SUTType,
    SUTConfigLoader,
    resolve_sut_url,
)


def _get_project_root(project_dir: str = ".") -> Path:
    """获取项目根目录"""
    return Path(project_dir).resolve()


@click.group()
def sut():
    """SUT (被测系统) 环境配置管理"""
    pass


@sut.command("init")
@click.argument("env", default="local")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--base-url", help="显式指定 base URL")
@click.option("--sut-type", default="web", type=click.Choice(["web", "api", "mobile", "desktop", "microservice"]), help="SUT 类型")
def init(env: str, project_dir: str, base_url: Optional[str], sut_type: str):
    """初始化 SUT 配置到运行时目录"""

    project_root = _get_project_root(project_dir)
    loader = SUTConfigLoader(project_root)

    # 创建默认配置
    config = SUTConfig.from_env(env, base_url=base_url or "", sut_type=SUTType(sut_type))
    config.name = f"{env}-default"

    # 保存配置
    config_path = loader.save(env, config)

    click.echo(f"[OK] SUT 配置已初始化")
    click.echo(f"  环境: {env}")
    click.echo(f"  类型: {sut_type}")
    click.echo(f"  URL: {config.base_url}")
    click.echo(f"  配置: {config_path}")


@sut.command("show")
@click.argument("env", default="local")
@click.option("--project-dir", default=".", help="项目目录")
def show(env: str, project_dir: str):
    """显示指定环境的 SUT 配置"""

    project_root = _get_project_root(project_dir)
    loader = SUTConfigLoader(project_root)

    # 尝试加载配置
    config = loader.load(env)

    if config:
        click.echo(f"[OK] 环境 '{env}' 的 SUT 配置:")
        click.echo(f"  类型: {config.sut_type.value}")
        click.echo(f"  名称: {config.name}")
        click.echo(f"  URL: {config.base_url}")
        click.echo(f"  路径: {config.base_path}")
        click.echo(f"  协议: {config.protocol}")
        if config.auth_type:
            click.echo(f"  认证: {config.auth_type}")
        if config.extras:
            click.echo(f"  扩展: {config.extras}")
    else:
        # 显示解析后的 URL
        url = resolve_sut_url(env)
        click.echo(f"[INFO] 环境 '{env}' 无配置文件，使用默认值:")
        click.echo(f"  URL: {url}")
        click.echo(f"  提示: 使用 'qa sut init {env}' 创建配置文件")


@sut.command("list")
@click.option("--project-dir", default=".", help="项目目录")
def list_(project_dir: str):
    """列出所有已配置的 SUT 环境"""

    project_root = _get_project_root(project_dir)
    loader = SUTConfigLoader(project_root)

    # 获取 tests 目录下的 runtime 目录
    tests_dir = loader._get_tests_dir()
    runtime_dir = tests_dir / "runtime"

    if not runtime_dir.exists():
        click.echo("[INFO] 暂无 SUT 配置，运行 'qa sut init <env>' 初始化")
        click.echo("")
        click.echo("默认环境配置:")
        for env_name in ["local", "test", "staging", "prod"]:
            url = resolve_sut_url(env_name)
            click.echo(f"  {env_name}: {url}")
        return

    # 查找所有环境配置
    env_configs = []
    for env_dir in sorted(runtime_dir.iterdir()):
        if env_dir.is_dir():
            config_file = env_dir / "sut.yaml"
            if config_file.exists():
                try:
                    with open(config_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        env_configs.append({
                            "name": env_dir.name,
                            "url": data.get("base_url", "N/A"),
                            "type": data.get("sut_type", "N/A"),
                        })
                except Exception:
                    pass

    if not env_configs:
        click.echo("[INFO] 暂无 SUT 配置，运行 'qa sut init <env>' 初始化")
        click.echo("")
        click.echo("默认环境配置:")
        for env_name in ["local", "test", "staging", "prod"]:
            url = resolve_sut_url(env_name)
            click.echo(f"  {env_name}: {url}")
        return

    click.echo("[OK] 已配置的 SUT 环境:")
    click.echo("")
    for config in env_configs:
        click.echo(f"  {config['name']}:")
        click.echo(f"    URL: {config['url']}")
        click.echo(f"    类型: {config['type']}")


@sut.command("set")
@click.argument("env")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--base-url", required=True, help="设置 base URL")
@click.option("--base-path", default="", help="设置 base path")
@click.option("--protocol", default="http", type=click.Choice(["http", "https"]), help="协议")
@click.option("--auth-type", default=None, type=click.Choice(["none", "bearer", "basic", "api_key"]), help="认证类型")
def set_config(
    env: str,
    project_dir: str,
    base_url: str,
    base_path: str,
    protocol: str,
    auth_type: Optional[str],
):
    """设置指定环境的 SUT 配置"""

    project_root = _get_project_root(project_dir)
    loader = SUTConfigLoader(project_root)

    # 创建或更新配置
    config = SUTConfig(
        sut_type=SUTType.WEB,
        name=f"{env}-custom",
        base_url=base_url,
        base_path=base_path,
        protocol=protocol,
        auth_type=auth_type,
    )

    config_path = loader.save(env, config)

    click.echo(f"[OK] SUT 配置已更新")
    click.echo(f"  环境: {env}")
    click.echo(f"  URL: {base_url}")
    click.echo(f"  配置: {config_path}")


@sut.command("url")
@click.argument("env", default="local")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--explicit-url", help="显式指定 URL（测试用）")
def url(env: str, project_dir: str, explicit_url: Optional[str]):
    """解析并显示指定环境的 URL"""

    project_root = _get_project_root(project_dir)
    loader = SUTConfigLoader(project_root)

    # 尝试从配置文件加载
    config = loader.load(env)

    if config:
        resolved_url = config.base_url
        if config.base_path:
            resolved_url = f"{resolved_url.rstrip('/')}/{config.base_path.lstrip('/')}"
    else:
        resolved_url = resolve_sut_url(env, explicit_url)

    click.echo(resolved_url)


@sut.command("resolve")
@click.argument("url_template")
@click.option("--env", default="local", help="环境名称")
def resolve(url_template: str, env: str):
    """解析 URL 模板（支持变量替换）"""

    # 支持的变量
    variables = {
        "env": env,
        "base_url": resolve_sut_url(env),
    }

    # 简单替换
    result = url_template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", value)

    click.echo(result)


# 为 list 命令创建别名（避免与 Python 关键字冲突）
list_.__name__ = "list"
