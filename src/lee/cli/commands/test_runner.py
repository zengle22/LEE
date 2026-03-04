"""
test_runner CLI — E2E 测试执行器 v0.3

支持本地和 Docker 两种执行模式，集成新的 QA 模块。

Exit Code 约定:
  0 — CLI 执行成功，且至少跑过一个用例（不代表所有都 PASS）
  1 — E2E 运行完成，但有用例失败（正常测试失败）
  2 — 环境/infra 级错误（Docker 启动失败、Playwright 无法执行）
  3 — 参数错误/输入不合法

日志采集:
  运行时会输出 [PATH-DEBUG] 前缀的调试日志，帮助诊断路径问题。
  使用 --log-file 选项可将日志保存到文件。
  使用 --verbose 选项可输出详细调试日志。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click


# ── Exit codes ──────────────────────────────────────────────
EXIT_SUCCESS = 0          # 跑完，至少有一个用例
EXIT_TEST_FAILURE = 1     # 跑完，有失败用例
EXIT_INFRA_ERROR = 2      # Docker/Playwright 基础设施错误
EXIT_INVALID_ARGS = 3     # 参数错误


# ── 日志配置 ────────────────────────────────────────────────
def _setup_logging(log_file: Optional[str] = None, verbose: bool = False):
    """配置日志输出

    Args:
        log_file: 日志文件路径（可选）
        verbose: 是否输出详细日志
    """
    log_level = logging.DEBUG if verbose else logging.INFO

    # 创建 logger
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # 清除现有 handler
    logger.handlers.clear()

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件 handler（如果指定了 log_file）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.info(f"[LOG] 日志将保存到：{log_file}")

    return logger


# ── 默认路径 ────────────────────────────────────────────────
_DEFAULT_RUNNER_SCRIPT = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..",          # src/lee/cli/commands → 项目根
    "spec-global", "departments", "qa",
    "skills", "e2e-runner", "v1", "scripts", "run-e2e-docker.sh",
)


# ── Click CLI ───────────────────────────────────────────────

@click.group()
def test_runner():
    """E2E 测试执行器 (test_runner v0.3)"""
    pass


@test_runner.command("run-e2e")
@click.option("--suite", required=True, help="测试套件名称（如 smoke / regression）")
@click.option("--env", "environment", required=True, help="目标测试环境（如 test / staging）")
@click.option("--test-set", "test_set", required=True,
              type=click.Path(exists=True), help="test-cases.yaml 文件路径")
@click.option("--out-dir", "out_dir", required=True,
              type=click.Path(), help="Artifacts 输出目录")
@click.option("--report-json", "report_json", required=True,
              type=click.Path(), help="标准化 e2e-report.json 输出路径")
@click.option("--base-url", default=None, help="被测应用 URL（覆盖环境默认值）")
@click.option("--runner-script", default=None,
              help="run-e2e-docker.sh 路径（默认取 spec-global 下）")
@click.option("--docker-image", default="e2e-runner:latest", help="Docker 镜像名")
@click.option("--mode", default="docker", type=click.Choice(["local", "docker"]),
              help="执行模式：local（本地）或 docker（容器）")
@click.option("--log-file", default=None, type=click.Path(),
              help="日志文件路径（可选）")
@click.option("-v", "--verbose", is_flag=True,
              help="输出详细日志（包括路径调试信息）")
def run_e2e(
    suite: str,
    environment: str,
    test_set: str,
    out_dir: str,
    report_json: str,
    base_url: Optional[str],
    runner_script: Optional[str],
    docker_image: str,
    mode: str,
    log_file: Optional[str],
    verbose: bool,
) -> None:
    """执行 E2E Playwright 测试套件，产出标准化报告。

    v0.3 新增:
      - --mode 参数支持本地执行
      - --log-file 参数保存日志到文件
      - --verbose 参数输出详细调试日志
    """
    # 配置日志
    logger = _setup_logging(log_file, verbose)
    logger.info(f"[INFO] test_runner 启动 - 模式：{mode}")
    logger.info(f"[INFO] 参数：suite={suite}, env={environment}, test_set={test_set}")

    # 1. 校验参数 ─────────────────────────────────────────
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    report_path = Path(report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # 2. 选择执行模式 ─────────────────────────────────────
    if mode == "local":
        exit_code = _run_local(
            suite=suite,
            environment=environment,
            test_set=test_set,
            out_dir=out_path,
            report_path=report_path,
            base_url=base_url,
        )
    else:  # docker
        exit_code = _run_docker(
            suite=suite,
            environment=environment,
            test_set=test_set,
            out_dir=out_path,
            report_path=report_path,
            base_url=base_url,
            runner_script=runner_script,
            docker_image=docker_image,
        )

    # 3. 错误分类（仅失败时） ───────────────────────────
    if exit_code == EXIT_TEST_FAILURE:
        _classify_failure(report_path, logger)

    sys.exit(exit_code)


def _classify_failure(report_path: Path, logger: logging.Logger) -> None:
    """使用 QA 模块进行错误分类"""
    try:
        from lee.qa.classifier.error_classifier import ErrorClassifier
        import yaml

        with open(report_path, encoding="utf-8") as f:
            report = yaml.safe_load(f)

        classifier = ErrorClassifier()
        result = classifier.classify(report)

        logger.info(f"[ERROR-CLASSIFICATION] Error Type: {result.error_type}")
        logger.info(f"[ERROR-CLASSIFICATION] Error Location: {result.error_location}")
        logger.info(f"[ERROR-CLASSIFICATION] Suggested Action: {result.suggested_action}")
        logger.info(f"[ERROR-CLASSIFICATION] Explanation: {result.explanation}")

    except Exception as e:
        logger.warning(f"[ERROR-CLASSIFICATION] 分类失败：{e}")


# ── 内部执行函数 ───────────────────────────────────────────

def _run_local(
    suite: str,
    environment: str,
    test_set: str,
    out_dir: Path,
    report_path: Path,
    base_url: Optional[str],
) -> int:
    """本地执行模式（使用新的 QA 模块）"""
    try:
        from lee.qa.runner.local import LocalRunner
        from lee.qa.runner.base import TestConfig
        from lee.qa.runner.sut import SUTConfigLoader, SUTType, resolve_sut_url
        from lee.qa.classifier.error_classifier import ErrorClassifier
        import yaml
    except ImportError as e:
        click.echo(f"[ERROR] QA 模块导入失败：{e}")
        return EXIT_INFRA_ERROR

    # 1. 加载测试用例
    with open(test_set, encoding="utf-8") as f:
        test_data = yaml.safe_load(f)

    # 提取 test_set_id 用于路径查找
    test_set_id = test_data.get("test_set_id", Path(test_set).stem)
    logger = logging.getLogger(__name__)
    logger.info(f"[INFO] test_set_id: {test_set_id}")
    logger.info(f"[INFO] 加载测试用例：{test_data.get('title', 'Unknown')}")

    # 2. 生成测试脚本（如果有 generator）
    scripts = _get_scripts_from_test_set(test_data, out_dir, test_set_id)
    if not scripts:
        _emit_error("没有找到测试脚本")
        return EXIT_INVALID_ARGS

    logger.info(f"[INFO] 找到 {len(scripts)} 个测试脚本")

    # 3. 解析 base_url（使用 SUT 配置）
    # 优先级：CLI --base-url > test_set.base_url > 环境默认值
    resolved_base_url = base_url
    if not resolved_base_url:
        # 尝试从 test_set 获取 base_url
        test_set_base_url = test_data.get("base_url")
        if test_set_base_url:
            resolved_base_url = test_set_base_url
        else:
            # 使用 SUT 配置解析
            resolved_base_url = resolve_sut_url(environment)

    logger.info(f"[INFO] 使用 base_url: {resolved_base_url}")

    # 4. 配置执行器
    config = TestConfig(
        scripts=scripts,
        base_url=resolved_base_url,
        output_dir=out_dir / "output",
        headless=True,
        environment=environment,
        sut_type=SUTType.WEB,
    )

    # 5. 检查环境
    runner = LocalRunner(config)
    env_checks = runner.check_environment()

    if not all(env_checks.values()):
        missing = [k for k, v in env_checks.items() if not v]
        _emit_error(f"环境检查失败：{', '.join(missing)}")
        return EXIT_INFRA_ERROR

    # 5. 执行测试
    result = runner.execute()

    # 6. 生成报告
    std_report = _transform_result_to_report(result, suite, environment)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(std_report, f, ensure_ascii=False, indent=2)

    # 7. 错误分类
    if result.exit_code >= 2:
        return EXIT_INFRA_ERROR
    elif result.failed > 0:
        return EXIT_TEST_FAILURE
    else:
        return EXIT_SUCCESS


def _run_docker(
    suite: str,
    environment: str,
    test_set: str,
    out_dir: Path,
    report_path: Path,
    base_url: Optional[str],
    runner_script: Optional[str],
    docker_image: str,
) -> int:
    """Docker 执行模式（原有逻辑）"""
    script = Path(runner_script) if runner_script else Path(_DEFAULT_RUNNER_SCRIPT).resolve()

    if not script.exists():
        # 如果脚本不存在，尝试使用新的 DockerRunner
        try:
            from lee.qa.runner.docker import DockerRunner
            from lee.qa.runner.base import TestConfig
            import yaml

            with open(test_set, encoding="utf-8") as f:
                test_data = yaml.safe_load(f)

            # 提取 test_set_id 用于路径查找
            test_set_id = test_data.get("test_set_id", Path(test_set).stem)
            logger = logging.getLogger(__name__)
            logger.info(f"[INFO] Docker 模式 - test_set_id: {test_set_id}")

            scripts = _get_scripts_from_test_set(test_data, out_dir, test_set_id)

            config = TestConfig(
                scripts=scripts,
                base_url=base_url or test_data.get("base_url", "http://localhost:3000"),
                output_dir=out_dir / "output",
                environment=environment,
            )

            runner = DockerRunner(config)
            env_checks = runner.check_environment()

            if not env_checks.get("docker"):
                _emit_error("Docker 不可用")
                return EXIT_INFRA_ERROR

            result = runner.execute()

            # 生成报告
            std_report = _transform_result_to_report(result, suite, environment)

            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(std_report, f, ensure_ascii=False, indent=2)

            if result.exit_code >= 2:
                return EXIT_INFRA_ERROR
            elif result.failed > 0:
                return EXIT_TEST_FAILURE
            else:
                return EXIT_SUCCESS

        except Exception as e:
            _emit_error(f"DockerRunner 执行失败：{e}")
            return EXIT_INFRA_ERROR
    else:
        # 原有的脚本执行逻辑
        cmd = [
            "bash",
            str(script),
            "--suite", suite,
            "--env", environment,
            "--test-set", str(test_set),
            "--out-dir", str(out_dir),
            "--report-json", str(report_path),
        ]

        if base_url:
            cmd.extend(["--base-url", base_url])

        if docker_image:
            cmd.extend(["--docker-image", docker_image])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return EXIT_SUCCESS
        elif result.returncode == 1:
            return EXIT_TEST_FAILURE
        else:
            _emit_error(f"Docker 脚本执行失败：{result.stderr}")
            return EXIT_INFRA_ERROR


def _emit_error(message: str) -> None:
    """输出错误信息"""
    click.echo(f"[ERROR] {message}", err=True)


def _get_scripts_from_test_set(test_data: Dict, out_dir: Path, test_set_id: str = None) -> List[Path]:
    """从 test set 获取脚本路径（支持双路径兼容）

    Args:
        test_data: test set 数据（包含 paths.scripts 配置）
        out_dir: artifacts 目录（通常是 evidence/）
        test_set_id: test set ID（用于日志和双路径查找）

    Returns:
        脚本路径列表

    路径查找优先级：
    1. test_data.paths.scripts（显式配置）
    2. out_dir.parent / "scripts"（结构推导）
    3. tse-{test_set_id}/scripts（原始 ID 路径）
    4. tse-{slugify(test_set_id)}/scripts（slugified 路径）
    """
    # 配置日志
    logger = logging.getLogger(__name__)

    # 记录调试信息
    logger.info(f"[PATH-DEBUG] test_set_id: {test_set_id}")
    logger.info(f"[PATH-DEBUG] out_dir: {out_dir}")
    logger.info(f"[PATH-DEBUG] test_data.paths: {test_data.get('paths', {})}")

    scripts_dir = None

    # 优先级 1: 使用 paths.scripts 配置
    scripts_path = test_data.get("paths", {}).get("scripts")
    if scripts_path:
        scripts_dir = Path(scripts_path)
        logger.info(f"[PATH-DEBUG] 使用 paths.scripts 配置：{scripts_dir}")
        if scripts_dir.exists():
            logger.info(f"[PATH-DEBUG] 目录存在，找到脚本")

    if scripts_dir is None or not scripts_dir.exists():
        # 优先级 2: 回退到 out_dir 的父目录
        scripts_dir = out_dir.parent / "scripts"
        logger.info(f"[PATH-DEBUG] 回退到 out_dir.parent: {scripts_dir}")

        if not scripts_dir.exists():
            # 优先级 3: 尝试原始 test_set_id 路径
            if test_set_id:
                original_path = out_dir.parent.parent / f"tse-{test_set_id}" / "scripts"
                logger.info(f"[PATH-DEBUG] 尝试原始 test_set_id 路径：{original_path}")
                if original_path.exists():
                    scripts_dir = original_path
                    logger.info(f"[PATH-DEBUG] 找到原始路径目录")

            # 优先级 4: 尝试 slugified 路径
            if test_set_id and not scripts_dir.exists():
                from lee.orchestrator.core.template_engine import _slugify
                slugified_id = _slugify(test_set_id)
                slugified_path = out_dir.parent.parent / f"tse-{slugified_id}" / "scripts"
                logger.info(f"[PATH-DEBUG] 尝试 slugified 路径：{slugified_path}")
                if slugified_path.exists():
                    scripts_dir = slugified_path
                    logger.info(f"[PATH-DEBUG] 找到 slugified 路径目录")

    # 记录最终选择的目录
    logger.info(f"[PATH-DEBUG] 最终脚本目录：{scripts_dir}")
    logger.info(f"[PATH-DEBUG] 目录存在：{scripts_dir.exists() if scripts_dir else 'N/A'}")

    scripts = []

    # 查找已存在的脚本
    if scripts_dir and scripts_dir.exists():
        # 使用 rglob 递归查找所有子目录中的脚本
        # Python 测试脚本
        scripts = list(scripts_dir.rglob("test_*.py"))
        scripts.extend(scripts_dir.rglob("*_test.py"))
        # TypeScript 测试脚本 (Playwright)
        scripts.extend(scripts_dir.rglob("*.spec.ts"))
        scripts.extend(scripts_dir.rglob("*.test.ts"))

        logger.info(f"[PATH-DEBUG] 找到的脚本数量：{len(scripts)}")
        for script in scripts:
            logger.info(f"[PATH-DEBUG]   - {script}")
    else:
        logger.warning(f"[PATH-DEBUG] 脚本目录不存在：{scripts_dir}")
        if out_dir.parent.exists():
            logger.warning(f"[PATH-DEBUG] 父目录内容：{list(out_dir.parent.iterdir())}")

    # 如果没有脚本，返回空列表（需要先生成）
    return scripts


def _transform_result_to_report(result, suite: str, environment: str) -> Dict:
    """将 TestResult 转换为标准报告"""
    cases = []
    for case in result.cases:
        case_data = {
            "id": case.case_id,
            "status": case.status,
            "duration_ms": case.duration_ms,
        }
        if case.error:
            case_data["error_message"] = case.error
        if case.error_type:
            case_data["error_type"] = case.error_type
        if case.screenshot_path:
            case_data["screenshot"] = case.screenshot_path
        cases.append(case_data)

    return {
        "suite": suite,
        "env": environment,
        "total": result.total,
        "passed": result.passed,
        "failed": result.failed,
        "skipped": result.skipped,
        "cases": cases,
    }


# ── 原有工具函数 ────────────────────────────────────────────

def _classify_failure(report_path: Path) -> None:
    """
    使用 QA 错误分类模块分析失败原因

    v0.2 新增功能
    """
    try:
        from lee.qa.classifier.error_classifier import ErrorClassifier
        import yaml

        with open(report_path, encoding="utf-8") as f:
            report = yaml.safe_load(f)

        classifier = ErrorClassifier()
        result = classifier.classify(report)

        click.echo("\n=== 错误分类 ===")
        click.echo(f"Error Type: {result.error_type}")
        click.echo(f"Error Location: {result.error_location}")
        click.echo(f"Suggested Action: {result.suggested_action}")
        click.echo(f"Explanation: {result.explanation}")

    except Exception as e:
        click.echo(f"[WARN] 错误分类失败：{e}")


if __name__ == "__main__":
    test_runner()
