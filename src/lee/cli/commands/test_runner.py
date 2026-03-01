"""
test_runner CLI — E2E 测试执行器 v0.2

支持本地和 Docker 两种执行模式，集成新的 QA 模块。

Exit Code 约定:
  0 — CLI 执行成功，且至少跑过一个用例（不代表所有都 PASS）
  1 — E2E 运行完成，但有用例失败（正常测试失败）
  2 — 环境/infra 级错误（Docker 启动失败、Playwright 无法执行）
  3 — 参数错误/输入不合法
"""

from __future__ import annotations

import json
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
    """E2E 测试执行器 (test_runner v0.2)"""
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
              help="执行模式: local（本地）或 docker（容器）")
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
) -> None:
    """执行 E2E Playwright 测试套件，产出标准化报告。

    v0.2 新增:
      - --mode 参数支持本地执行
      - 集成新的 QA 模块进行错误分类
    """

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

    sys.exit(exit_code)


@test_runner.command("validate")
@click.option("--code", "code_path", required=True,
              type=click.Path(exists=True), help="Python 测试代码文件")
def validate_code(code_path: str) -> None:
    """验证生成的测试代码质量。

    使用 QA 模块的多层验证器检查代码。
    """
    try:
        from lee.qa.validator.schema_validator import SchemaValidator
        from lee.qa.validator.syntax_validator import SyntaxValidator
        from lee.qa.validator.selector_validator import SelectorValidator
        from lee.qa.validator.timeout_validator import TimeoutValidator
    except ImportError:
        click.echo("[ERROR] QA 模块未安装", err=True)
        sys.exit(EXIT_INFRA_ERROR)

    code = Path(code_path).read_text(encoding="utf-8")

    # 运行所有验证层
    results = {
        "L1_Schema": SchemaValidator.validate(code),
        "L2_Syntax": SyntaxValidator.validate(code),
        "L3_Selector": SelectorValidator.validate(code),
        "L3_Timeout": TimeoutValidator.validate(code),
    }

    # 汇总结果
    all_valid = all(r.is_valid for r in results.values())

    for layer, result in results.items():
        status = "✓" if result.is_valid else "✗"
        click.echo(f"{status} {layer}: {len(result.errors)} errors, {len(result.warnings)} warnings")

        if result.errors:
            for err in result.errors:
                click.echo(f"  - ERROR: {err['category']}: {err['message']}", err=True)

        if result.warnings:
            for warn in result.warnings:
                click.echo(f"  - WARN: {warn['category']}: {warn['message']}", err=True)

    sys.exit(EXIT_SUCCESS if all_valid else EXIT_TEST_FAILURE)


@test_runner.command("classify")
@click.option("--error", "error_msg", required=True, help="错误消息")
def classify_error(error_msg: str) -> None:
    """分类测试错误为 code_issue 或 system_issue。"""
    try:
        from lee.qa.classifier.error_classifier import ErrorClassifier
    except ImportError:
        click.echo("[ERROR] QA 模块未安装", err=True)
        sys.exit(EXIT_INFRA_ERROR)

    result = ErrorClassifier.classify(error_msg)

    click.echo(f"Type: {result.type}")
    click.echo(f"Category: {result.category}")
    click.echo(f"Confidence: {result.confidence}")
    click.echo(f"Is False Fail: {result.is_false_fail}")
    click.echo(f"Suggested Action: {result.suggested_action}")
    click.echo(f"Explanation: {result.explanation}")

    sys.exit(EXIT_SUCCESS)


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
        from lee.qa.classifier.error_classifier import ErrorClassifier
        import yaml
    except ImportError as e:
        _emit_error(f"QA 模块导入失败: {e}")
        return EXIT_INFRA_ERROR

    # 1. 加载测试用例
    with open(test_set, encoding="utf-8") as f:
        test_data = yaml.safe_load(f)

    # 2. 生成测试脚本（如果有 generator）
    scripts = _get_scripts_from_test_set(test_data, out_dir)
    if not scripts:
        _emit_error("没有找到测试脚本")
        return EXIT_INVALID_ARGS

    # 3. 配置执行器
    config = TestConfig(
        scripts=scripts,
        base_url=base_url or test_data.get("base_url", "http://localhost:3000"),
        output_dir=out_dir / "output",
        headless=True,
        environment=environment,
    )

    # 4. 检查环境
    runner = LocalRunner(config)
    env_checks = runner.check_environment()

    if not all(env_checks.values()):
        missing = [k for k, v in env_checks.items() if not v]
        _emit_error(f"环境检查失败: {', '.join(missing)}")
        return EXIT_INFRA_ERROR

    # 5. 执行测试
    result = runner.execute()

    # 6. 生成报告
    std_report = _transform_result_to_report(result, suite, environment)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(std_report, f, ensure_ascii=False, indent=2)

    click.echo(f"[test_runner] 报告已写入: {report_path}", err=True)

    # 7. 确定退出码
    if result.exit_code >= 2:
        return EXIT_INFRA_ERROR
    elif result.failed > 0:
        return EXIT_TEST_FAILURE
    elif result.total == 0:
        return EXIT_INFRA_ERROR
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

            scripts = _get_scripts_from_test_set(test_data, out_dir)

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
            _emit_error(f"DockerRunner 执行失败: {e}")
            return EXIT_INFRA_ERROR
    else:
        # 原有的脚本执行逻辑
        return _run_docker_script(
            suite=suite,
            environment=environment,
            test_set=test_set,
            out_dir=out_dir,
            report_path=report_path,
            base_url=base_url,
            script=script,
            docker_image=docker_image,
        )


def _run_docker_script(
    suite: str,
    environment: str,
    test_set: str,
    out_dir: Path,
    report_path: Path,
    base_url: Optional[str],
    script: Path,
    docker_image: str,
) -> int:
    """执行 Docker 脚本（原有逻辑）"""
    # 1. 构造环境变量
    env = os.environ.copy()
    env.update({
        "LEE_ENV": environment,
        "SUITE": suite,
        "TEST_SET_PATH": str(Path(test_set).resolve()),
        "WORK_DIR": str(out_dir.resolve()),
        "DOCKER_IMAGE": docker_image,
    })
    if base_url:
        env["BASE_URL"] = base_url

    # 2. 调用脚本
    click.echo(f"[test_runner] 开始执行: suite={suite} env={environment}", err=True)

    try:
        result = subprocess.run(
            [str(script)],
            env=env,
            cwd=str(out_dir),
            capture_output=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )
        docker_exit = result.returncode

        if result.stderr:
            sys.stderr.buffer.write(result.stderr)
        if result.stdout:
            sys.stderr.buffer.write(result.stdout)

    except FileNotFoundError:
        _emit_error(f"无法执行脚本: {script}")
        return EXIT_INFRA_ERROR
    except subprocess.TimeoutExpired:
        _emit_error("Runner 执行超时（600s）")
        return EXIT_INFRA_ERROR
    except Exception as exc:
        _emit_error(f"Runner 执行异常: {exc}")
        return EXIT_INFRA_ERROR

    # 3. 收集报告并转换
    pw_report_candidates = [
        out_dir / "output" / "e2e-report.json",
        out_dir / "e2e-report.json",
    ]
    pw_report = None
    for candidate in pw_report_candidates:
        if candidate.exists():
            pw_report = candidate
            break

    if pw_report and pw_report.exists():
        try:
            with open(pw_report, "r", encoding="utf-8") as f:
                pw_data = json.load(f)
            std_report = _transform_playwright_report(pw_data, suite, environment, out_dir)
        except Exception as exc:
            _emit_error(f"Playwright 报告解析失败: {exc}")
            return EXIT_INFRA_ERROR
    else:
        std_report = {
            "suite": suite,
            "env": environment,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "cases": [],
        }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(std_report, f, ensure_ascii=False, indent=2)

    # 4. 确定退出码
    total = std_report.get("total", 0)
    failed = std_report.get("failed", 0)

    if docker_exit >= 2:
        return EXIT_INFRA_ERROR
    elif total == 0:
        return EXIT_INFRA_ERROR
    elif failed > 0:
        return EXIT_TEST_FAILURE
    else:
        return EXIT_SUCCESS


def _get_scripts_from_test_set(test_data: Dict, out_dir: Path) -> List[Path]:
    """从 test set 获取脚本路径"""
    # 优先使用 tse.yaml 中 paths.scripts 配置
    scripts_path = test_data.get("paths", {}).get("scripts")
    if scripts_path:
        scripts_dir = Path(scripts_path)
    else:
        scripts_dir = out_dir / "scripts"
    scripts = []

    # 查找已存在的脚本
    if scripts_dir.exists():
        # 使用 rglob 递归查找所有子目录中的脚本
        # Python 测试脚本
        scripts = list(scripts_dir.rglob("test_*.py"))
        scripts.extend(scripts_dir.rglob("*_test.py"))
        # TypeScript 测试脚本 (Playwright)
        scripts.extend(scripts_dir.rglob("*.spec.ts"))
        scripts.extend(scripts_dir.rglob("*.test.ts"))

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

def _emit_error(message: str) -> None:
    """向 stderr 输出结构化错误。"""
    click.echo(f"[test_runner][ERROR] {message}", err=True)


def _transform_playwright_report(
    pw_data: Dict[str, Any],
    suite: str,
    environment: str,
    out_dir: Path,
) -> Dict[str, Any]:
    """把 Playwright JSON reporter 的输出转为标准 e2e-report.json。"""

    cases: List[Dict[str, Any]] = []
    total = 0
    passed = 0
    failed = 0

    for pw_suite in pw_data.get("suites", []):
        for spec in pw_suite.get("specs", []):
            for test in spec.get("tests", []):
                for result in test.get("results", []):
                    total += 1
                    test_id = spec.get("title", f"test_{total}")
                    status = result.get("status", "unknown")

                    if status in ("passed", "expected"):
                        passed += 1
                        mapped_status = "passed"
                    elif status in ("failed", "unexpected"):
                        failed += 1
                        mapped_status = "failed"
                    else:
                        mapped_status = status

                    error_msg = None
                    error_type = None
                    if mapped_status == "failed":
                        error_obj = result.get("error", {})
                        error_msg = (
                            error_obj.get("message", "")
                            if isinstance(error_obj, dict)
                            else str(error_obj)
                        )
                        error_type = _classify_error(error_msg, status)

                    attachments = result.get("attachments", [])
                    screenshot = _find_attachment(attachments, "screenshot", out_dir)
                    trace = _find_attachment(attachments, "trace", out_dir)

                    cases.append({
                        "id": test_id,
                        "status": mapped_status,
                        "error_type": error_type,
                        "duration_ms": result.get("duration", 0),
                        "error_message": error_msg,
                        "screenshot": screenshot,
                        "trace": trace,
                        "logs": None,
                    })

    return {
        "suite": suite,
        "env": environment,
        "total": total,
        "passed": passed,
        "failed": failed,
        "cases": cases,
    }


def _classify_error(error_msg: str, pw_status: str) -> str:
    """根据错误信息做粗略分类。"""
    if not error_msg:
        return "script_error"

    lower = error_msg.lower()

    infra_keywords = [
        "econnrefused", "enotfound", "dns", "etimedout",
        "net::err_", "network error", "socket hang up",
    ]
    for kw in infra_keywords:
        if kw in lower:
            return "infra_error"

    script_keywords = ["timeout", "locator", "waitfor", "selector"]
    for kw in script_keywords:
        if kw in lower:
            return "script_error"

    assertion_keywords = ["expect", "assert", "toBe", "toHave", "toEqual", "toContain"]
    for kw in assertion_keywords:
        if kw in lower:
            return "assertion_failed"

    return "assertion_failed" if pw_status in ("failed", "unexpected") else "script_error"


def _find_attachment(
    attachments: List[Dict[str, Any]],
    content_type_prefix: str,
    out_dir: Path,
) -> Optional[str]:
    """在 Playwright 结果的 attachments 中查找指定类型。"""
    for att in attachments:
        name = att.get("name", "").lower()
        ct = att.get("contentType", "").lower()
        path = att.get("path", "")
        if content_type_prefix in name or content_type_prefix in ct:
            if path:
                try:
                    return str(Path(path).relative_to(out_dir))
                except ValueError:
                    return path
    return None
