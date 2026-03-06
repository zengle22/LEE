#!/usr/bin/env python3
"""
Contract-driven SSOT chain demo.

运行方式:
    python demo_ssot_contract_chain.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTContractMaterializer


def build_demo_contract() -> dict:
    return {
        "contract_version": "1.0",
        "workflow_id": "demo.ssot.full_chain",
        "run_id": "demo-contract-run-001",
        "outputs": [
            {
                "key": "epic",
                "identity_kind": "ssot",
                "ssot_type": "epic",
                "title": "增长基础设施",
                "content": "# 增长基础设施\n\n## 范围\n- 注册\n- 激活\n- 转化\n",
                "source_refs": ["SRC-001#1.2"]
            },
            {
                "key": "feat",
                "identity_kind": "ssot",
                "ssot_type": "feat",
                "title": "用户注册",
                "parent": "epic",
                "content": "# 用户注册\n\n## 目标\n- 手机号注册\n- 邮箱注册\n",
                "source_refs": ["epic#scope"]
            },
            {
                "key": "ui",
                "identity_kind": "ssot",
                "ssot_type": "ui",
                "title": "注册页原型",
                "parent": "feat",
                "implements": ["feat"],
                "content": "# 注册页原型\n"
            },
            {
                "key": "tech",
                "identity_kind": "ssot",
                "ssot_type": "tech",
                "title": "注册服务设计",
                "parent": "feat",
                "implements": ["feat"],
                "content": "# 注册服务设计\n"
            },
            {
                "key": "task",
                "identity_kind": "ssot",
                "ssot_type": "task",
                "title": "实现注册接口",
                "parent": "feat",
                "implements": ["feat"],
                "content": "# 实现注册接口\n"
            },
            {
                "key": "testset",
                "identity_kind": "ssot",
                "ssot_type": "testset",
                "title": "用户注册测试集",
                "parent": "feat",
                "verifies": ["feat"],
                "content": "# 用户注册测试集\n"
            },
            {
                "key": "tc",
                "identity_kind": "ssot",
                "ssot_type": "tc",
                "title": "邮箱已存在时注册失败",
                "parent": "testset",
                "verifies": ["feat"],
                "content": "# 邮箱已存在时注册失败\n"
            },
            {
                "key": "report",
                "identity_kind": "ssot",
                "ssot_type": "report",
                "title": "注册功能验收报告",
                "parent": "feat",
                "verifies": ["feat", "testset", "tc"],
                "content": "# 注册功能验收报告\n"
            },
            {
                "key": "bug",
                "identity_kind": "ssot",
                "ssot_type": "bug",
                "title": "重复邮箱错误码不一致",
                "parent": "tc",
                "verifies": ["tc", "feat"],
                "content": "# 重复邮箱错误码不一致\n"
            },
            {
                "key": "evi",
                "identity_kind": "ssot",
                "ssot_type": "evi",
                "title": "注册失败抓包证据",
                "parent": "bug",
                "verifies": ["bug", "tc"],
                "content": "# 注册失败抓包证据\n"
            },
            {
                "key": "retrospective_note",
                "identity_kind": "non_ssot",
                "artifact_type": "DOCUMENT",
                "category": "readme",
                "governance_kind": "knowledge",
                "title": "注册链路复盘记录",
                "depends_on": ["report", "bug"],
                "content": "# 复盘\n\n- 登录链路正常\n- 注册错误码需要统一\n"
            }
        ]
    }


def run_demo() -> None:
    base = Path("demo-test-artifacts/ssot-contract-chain-demo-20260306").resolve()
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    manager = ArtifactManager(root_path=base / ".artifacts", project_root=base)
    materializer = SSOTContractMaterializer(manager)
    contract = build_demo_contract()
    outputs = materializer.materialize(contract)

    summary = {
        "project_root": str(base),
        "schema": str(materializer.schema_path),
        "outputs": {
            key: {
                "id": item.artifact.id,
                "identity_kind": item.identity_kind,
                "path_root": item.artifact.path_root,
                "path": item.artifact.path,
                "absolute_path": str(item.artifact.absolute_path),
                "parent_id": item.artifact.properties.get("parent_id"),
                "verifies": item.artifact.verifies,
                "implements": item.artifact.implements,
            }
            for key, item in outputs.items()
        },
        "created_files": sorted(
            str(path.relative_to(base)).replace("\\", "/")
            for path in base.rglob("*")
            if path.is_file()
        ),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_demo()
