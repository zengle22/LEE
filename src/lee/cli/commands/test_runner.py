"""
test_runner CLI — E2E 测试执行器 v0.1

封装 Docker + Playwright 执行，产出标准化 e2e-report.json。

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
    """E2E 测试执行器 (test_runner v0.1)"""
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
def run_e2e(
    suite: str,
    environment: str,
    test_set: str,
    out_dir: str,
    report_json: str,
    base_url: Optional[str],
    runner_script: Optional[str],
    docker_image: str,
) -> None:
    """执行 E2E Playwright 测试套件，产出标准化报告。"""

    # 1. 校验参数 ─────────────────────────────────────────
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    report_path = Path(report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    script = Path(runner_script) if runner_script else Path(_DEFAULT_RUNNER_SCRIPT).resolve()
    if not script.exists():
        _emit_error(f"Runner script 不存在: {script}")
        sys.exit(EXIT_INVALID_ARGS)
    if not os.access(script, os.X_OK):
        _emit_error(f"Runner script 不可执行: {script}")
        sys.exit(EXIT_INVALID_ARGS)

    # 2. 构造环境变量 ─────────────────────────────────────
    env = os.environ.copy()
    env.update({
        "LEE_ENV": environment,
        "SUITE": suite,
        "TEST_SET_PATH": str(Path(test_set).resolve()),
        "WORK_DIR": str(out_path.resolve()),
        "DOCKER_IMAGE": docker_image,
    })
    if base_url:
        env["BASE_URL"] = base_url

    # 3. 调用 run-e2e-docker.sh ──────────────────────────
    click.echo(f"[test_runner] 开始执行: suite={suite} env={environment}", err=True)
    click.echo(f"[test_runner] runner script: {script}", err=True)
    click.echo(f"[test_runner] out-dir: {out_path}", err=True)

    try:
        result = subprocess.run(
            [str(script)],
            env=env,
            cwd=str(out_path),
            capture_output=False,          # 让 stdout/stderr 直接流向 stderr
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,                   # 10 分钟硬超时
        )
        docker_exit = result.returncode
        # 把 shell 脚本的 stdout/stderr 流到自己的 stderr
        if result.stderr:
            sys.stderr.buffer.write(result.stderr)
        if result.stdout:
            sys.stderr.buffer.write(result.stdout)
    except FileNotFoundError:
        _emit_error(f"无法执行脚本: {script}")
        sys.exit(EXIT_INFRA_ERROR)
    except subprocess.TimeoutExpired:
        _emit_error("Runner 执行超时（600s）")
        sys.exit(EXIT_INFRA_ERROR)
    except Exception as exc:
        _emit_error(f"Runner 执行异常: {exc}")
        sys.exit(EXIT_INFRA_ERROR)

    click.echo(f"[test_runner] Docker exit code: {docker_exit}", err=True)

    # 4. 收集 Playwright JSON 报告 ──────────────────────
    # playwright.config.ts 输出到 output/e2e-report.json (相对 WORK_DIR)
    pw_report_candidates = [
        out_path / "output" / "e2e-report.json",
        out_path / "e2e-report.json",
    ]
    pw_report = None
    for candidate in pw_report_candidates:
        if candidate.exists():
            pw_report = candidate
            break

    if pw_report is None and docker_exit not in (2, 3):
        # Docker 跑完了但没找到报告——当作 infra 错误
        _emit_error("Playwright JSON 报告未找到")
        sys.exit(EXIT_INFRA_ERROR)

    # 5. 转换为标准报告 ──────────────────────────────────
    if pw_report and pw_report.exists():
        try:
            with open(pw_report, "r", encoding="utf-8") as f:
                pw_data = json.load(f)
            std_report = _transform_playwright_report(pw_data, suite, environment, out_path)
        except Exception as exc:
            _emit_error(f"Playwright 报告解析失败: {exc}")
            sys.exit(EXIT_INFRA_ERROR)
    else:
        # Docker 就挂了，给一个空报告
        std_report = {
            "suite": suite,
            "env": environment,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "cases": [],
        }

    # 6. 写标准报告 ──────────────────────────────────────
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(std_report, f, ensure_ascii=False, indent=2)

    click.echo(f"[test_runner] 报告已写入: {report_path}", err=True)

    # 7. 确定最终 exit code ─────────────────────────────
    total = std_report.get("total", 0)
    failed = std_report.get("failed", 0)

    if docker_exit >= 2:
        final_exit = EXIT_INFRA_ERROR
    elif total == 0:
        # Docker exit 0 但没跑任何用例——也算 infra 问题
        final_exit = EXIT_INFRA_ERROR
    elif failed > 0:
        final_exit = EXIT_TEST_FAILURE
    else:
        final_exit = EXIT_SUCCESS

    # 8. stdout 输出 summary JSON ───────────────────────
    summary = {
        "report_json": str(report_path),
        "total": total,
        "passed": std_report.get("passed", 0),
        "failed": failed,
    }
    click.echo(json.dumps(summary, ensure_ascii=False))

    sys.exit(final_exit)


# ── 内部工具函数 ────────────────────────────────────────────

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

    # Playwright JSON reporter 结构: { suites: [...], stats: {...} }
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
                        mapped_status = status  # skipped, timedOut, etc.

                    # 错误信息
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

                    # Artifacts 路径（相对 out_dir）
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
                        "logs": None,  # v0.1 不解析日志路径
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

    # Infra 错误
    infra_keywords = [
        "econnrefused", "enotfound", "dns", "etimedout",
        "net::err_", "network error", "socket hang up",
    ]
    for kw in infra_keywords:
        if kw in lower:
            return "infra_error"

    # 超时 / Locator 错误 → script_error
    script_keywords = ["timeout", "locator", "waitfor", "selector"]
    for kw in script_keywords:
        if kw in lower:
            return "script_error"

    # 断言失败
    assertion_keywords = ["expect", "assert", "toBe", "toHave", "toEqual", "toContain"]
    for kw in assertion_keywords:
        if kw in lower:
            return "assertion_failed"

    # 默认
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
                # 尝试转为相对路径
                try:
                    return str(Path(path).relative_to(out_dir))
                except ValueError:
                    return path
    return None
