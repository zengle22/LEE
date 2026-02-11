"""
check_env CLI — QA E2E 环境探测工具 v0.1

在 test_runner 执行前检查必要的环境/工具是否就绪。

Exit Code 约定:
  0 — 所有检查通过
  2 — 有任何检查项失败
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click


# ── 默认值 ──────────────────────────────────────────────────
_DEFAULT_RUNNER_SCRIPT = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..",
    "spec-global", "departments", "qa",
    "skills", "e2e-runner", "v1", "scripts", "run-e2e-docker.sh",
)

_DEFAULT_DOCKER_IMAGE = "e2e-runner:latest"


# ── Click CLI ───────────────────────────────────────────────

@click.group()
def check_env():
    """环境探测工具 (check_env v0.1)"""
    pass


@check_env.command("qa-e2e")
@click.option("--require-docker/--no-require-docker", default=True,
              help="是否要求 Docker")
@click.option("--require-script", default=None,
              help="run-e2e-docker.sh 路径（默认自动定位）")
@click.option("--require-image", default=_DEFAULT_DOCKER_IMAGE,
              help="Docker 镜像名")
@click.option("--base-url", default=None,
              help="可选：对被测应用 URL 做可达性探测")
def qa_e2e(
    require_docker: bool,
    require_script: Optional[str],
    require_image: str,
    base_url: Optional[str],
) -> None:
    """检查 QA E2E Runner 所需的工具和环境。"""

    checks: List[Dict[str, Any]] = []

    # 1. Docker 检查
    if require_docker:
        checks.append(_check_docker())

    # 2. Runner 脚本检查
    script_path = require_script or str(Path(_DEFAULT_RUNNER_SCRIPT).resolve())
    checks.append(_check_script(script_path))

    # 3. Docker 镜像检查
    if require_docker and require_image:
        checks.append(_check_docker_image(require_image))

    # 4. 可选：URL 可达性
    if base_url:
        checks.append(_check_url_reachable(base_url))

    # 输出结果
    all_ok = all(c["ok"] for c in checks)
    result = {
        "ok": all_ok,
        "checks": checks,
    }

    click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if all_ok else 2)


# ── 检查函数 ────────────────────────────────────────────────

def _check_docker() -> Dict[str, Any]:
    """检查 docker 是否在 PATH。"""
    if shutil.which("docker") is None:
        return {"name": "docker", "ok": False, "message": "docker not found in PATH"}

    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {
                "name": "docker",
                "ok": False,
                "message": f"docker version failed: {result.stderr.strip()}",
            }
        return {
            "name": "docker",
            "ok": True,
            "version": result.stdout.strip(),
        }
    except Exception as exc:
        return {"name": "docker", "ok": False, "message": str(exc)}


def _check_script(script_path: str) -> Dict[str, Any]:
    """检查 runner 脚本是否存在且可执行。"""
    p = Path(script_path)
    if not p.exists():
        return {
            "name": "run_e2e_script",
            "ok": False,
            "message": f"script not found: {script_path}",
        }
    if not os.access(p, os.X_OK):
        return {
            "name": "run_e2e_script",
            "ok": False,
            "message": f"script not executable: {script_path}",
        }
    return {"name": "run_e2e_script", "ok": True}


def _check_docker_image(image_name: str) -> Dict[str, Any]:
    """检查 Docker 镜像是否已构建。"""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip()
        if not output:
            return {
                "name": "docker_image",
                "ok": False,
                "message": f"image {image_name} not found",
            }
        return {"name": "docker_image", "ok": True, "image": image_name}
    except Exception as exc:
        return {"name": "docker_image", "ok": False, "message": str(exc)}


def _check_url_reachable(url: str) -> Dict[str, Any]:
    """用 curl 探测 URL 是否可达。"""
    curl = shutil.which("curl")
    if curl is None:
        return {
            "name": "url_reachable",
            "ok": False,
            "message": "curl not found in PATH",
        }

    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--connect-timeout", "5", "--max-time", "10", url],
            capture_output=True, text=True, timeout=15,
        )
        status_code = result.stdout.strip()
        if status_code and status_code[0] in ("2", "3"):
            return {"name": "url_reachable", "ok": True, "url": url,
                    "http_status": status_code}
        return {
            "name": "url_reachable",
            "ok": False,
            "message": f"HTTP {status_code} from {url}",
        }
    except Exception as exc:
        return {"name": "url_reachable", "ok": False, "message": str(exc)}
