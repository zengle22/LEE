#!/usr/bin/env python
"""Deterministic reverse EPIC/FEAT workflow helpers."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml
from jsonschema import ValidationError, validate


SRC_EXTENSIONS = {".go", ".ts", ".tsx", ".js", ".jsx", ".vue", ".py", ".sql", ".json", ".yaml", ".yml", ".md"}
EVIDENCE_STRATEGY = {
    "primary_selection": "ordered_impl_api_first",
    "ranking_signals": ["path_quality", "semantic_path_match", "page_content_match", "onboarding_local_rerank"],
}


CANDIDATE_CAPABILITIES: List[Dict[str, Any]] = [
    {
        "id": "CAP-001",
        "name": "工作流模板与实例生成",
        "summary": "维护 workflow 模板、注册表，并将模板渲染为运行时 instance。",
        "boundary": "覆盖模板文件、registry 与 template 渲染链，不包含具体业务步骤执行。",
        "code_refs": [
            "config/workflow-registry.yaml",
            "spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml",
            "src/lee/cli/commands/run.py",
            "src/lee/orchestrator/execution/template_manager.py",
        ],
        "features": [
            {
                "id": "FEAT-001",
                "key": "feat_register_workflow_templates",
                "title": "注册工作流模板",
                "summary": "通过 workflow registry 暴露模板定义与参数约束。",
                "scope": [
                    "在 registry 中声明 workflow key、path、kind 与参数集合。",
                    "为 CLI 提供稳定入口。",
                ],
                "inputs": ["workflow key", "template path", "required/optional params"],
                "outputs": ["可解析的 workflow registry entry"],
                "business_rules": [
                    "registry path 必须指向 checked-in template 文件。",
                    "模板 spec 只能被描述为模板，不能被视为运行时 instance。",
                ],
                "acceptance_criteria": [
                    "给定 workflow key 时，CLI 可以解析到模板路径。",
                    "registry 中声明了必填参数 request_id、repo_root、objective。",
                ],
                "code_refs": [
                    "config/workflow-registry.yaml",
                    "src/lee/cli/commands/run.py",
                ],
            },
            {
                "id": "FEAT-002",
                "key": "feat_parse_l3_workflow_templates",
                "title": "解析 L3 workflow 模板",
                "summary": "将 L3 模板中的 stages/steps 解析为可调度步骤与依赖关系。",
                "scope": [
                    "解析 stage/step 顺序、outputs、depends_on 与 executor_type。",
                    "保留模板边界，不生成固定 instance 文件作为规范源。",
                ],
                "inputs": ["rendered template yaml"],
                "outputs": ["workflow steps", "dependency graph", "output specs"],
                "business_rules": [
                    "stage.depends_on 在当前引擎中必须映射到前序 step id。",
                    "kind=skill 的步骤默认走 shell executor。",
                ],
                "acceptance_criteria": [
                    "模板可被解析为 Step 列表且不存在循环依赖。",
                    "skill/gate 步骤拥有正确 executor_type。",
                ],
                "code_refs": [
                    "src/lee/orchestrator/execution/template_manager.py",
                    "src/lee/orchestrator/ir/converter.py",
                ],
            },
            {
                "id": "FEAT-003",
                "key": "feat_render_runtime_instances",
                "title": "渲染运行时 workflow instance",
                "summary": "通过 CLI 将模板与参数渲染为运行时 workflow instance 文件并创建实例。",
                "scope": [
                    "渲染模板变量、写入 .workflow/rendered。",
                    "调用 pm_workflow 创建运行时 workflow instance。",
                ],
                "inputs": ["template path", "params", "project_dir"],
                "outputs": [".workflow/rendered/*.yaml", "workflow instance id"],
                "business_rules": [
                    "rendered workflow 是运行时产物，不应被视为 checked-in spec。",
                    "load_spec_as_params 的 workflow 需把 --spec 载入 params。",
                ],
                "acceptance_criteria": [
                    "运行 lee run 后会生成 rendered yaml。",
                    "runtime instance 的 data.params 与 spec 文件内容一致。",
                ],
                "code_refs": [
                    "src/lee/cli/commands/run.py",
                    "src/lee/orchestrator/api.py",
                ],
            },
        ],
    },
    {
        "id": "CAP-002",
        "name": "工作流执行与门禁控制",
        "summary": "调度 workflow 步骤、持久化执行状态，并执行自动/人工 gate。",
        "boundary": "覆盖执行、状态机与 gate，不包含业务文档生成策略本身。",
        "code_refs": [
            "src/lee/orchestrator/execution/orchestrator.py",
            "src/lee/orchestrator/execution/state_machine.py",
            "src/lee/orchestrator/execution/runners/auto_check_gate_runner.py",
            "src/lee/orchestrator/execution/runners/shell_runner.py",
        ],
        "features": [
            {
                "id": "FEAT-004",
                "key": "feat_execute_step_dag",
                "title": "执行工作流步骤 DAG",
                "summary": "根据 depends_on 选择 ready step 并顺序推进 workflow。",
                "scope": [
                    "处理 step 调度、继续执行与完成汇总。",
                    "支持 skill、agent、gate 等步骤类型。",
                ],
                "inputs": ["workflow instance", "current step state"],
                "outputs": ["completed_steps", "next ready step", "workflow summary"],
                "business_rules": [
                    "只有所有依赖满足后步骤才可执行。",
                    "失败步骤必须显式标记 workflow 状态。",
                ],
                "acceptance_criteria": [
                    "多步 workflow 可按 depends_on 连续推进。",
                    "失败时 workflow 状态变为 failed。",
                ],
                "code_refs": [
                    "src/lee/orchestrator/execution/orchestrator.py",
                    "src/lee/orchestrator/execution/state_machine.py",
                ],
            },
            {
                "id": "FEAT-005",
                "key": "feat_evaluate_auto_check_gates",
                "title": "执行自动检查门禁",
                "summary": "把 step_outputs 扁平化并执行 blocker/major 表达式。",
                "scope": [
                    "构建 gate evaluation context。",
                    "在 gate fail 时阻塞或失败 workflow。",
                ],
                "inputs": ["gate expression", "step_outputs"],
                "outputs": ["gate pass/fail result"],
                "business_rules": [
                    "freeze 模式要求 blocker 与 major 均为 0。",
                    "gate 上下文允许直接访问 review 输出中的标量字段。",
                ],
                "acceptance_criteria": [
                    "review 输出 blocker_count=0 时 draft/publish gate 可通过。",
                    "freeze 模式下 major_count>0 会触发 gate fail。",
                ],
                "code_refs": [
                    "src/lee/orchestrator/execution/runners/auto_check_gate_runner.py",
                    "spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml",
                ],
            },
            {
                "id": "FEAT-006",
                "key": "feat_persist_step_outputs",
                "title": "持久化步骤输出与证据路径",
                "summary": "完成步骤时把 output dict 与 output paths 写入 workflow data。",
                "scope": [
                    "保存 paths、stdout 元数据与结构化字段。",
                    "为后续 gate 和 $outputs 引用提供输入。",
                ],
                "inputs": ["step output", "output specs"],
                "outputs": ["workflow.data.step_outputs"],
                "business_rules": [
                    "同一步骤重复执行时路径列表需要去重合并。",
                    "结构化 stdout 应合并到 step_outputs 顶层。",
                ],
                "acceptance_criteria": [
                    "完成步骤后 step_outputs 中可读取 paths。",
                    "gate 表达式可以直接使用 review 产生的 blocker_count。",
                ],
                "code_refs": [
                    "src/lee/orchestrator/execution/state_machine.py",
                    "src/lee/orchestrator/execution/runners/shell_runner.py",
                ],
            },
        ],
    },
    {
        "id": "CAP-003",
        "name": "CLI 工作流操作",
        "summary": "通过 CLI 触发运行、查询状态与审批 gate。",
        "boundary": "覆盖命令入口与用户交互，不包含 orchestrator 内部执行细节。",
        "code_refs": [
            "src/lee/cli/main.py",
            "src/lee/cli/commands/run.py",
            "src/lee/cli/commands/status.py",
            "src/lee/cli/commands/approve.py",
        ],
        "features": [
            {
                "id": "FEAT-007",
                "key": "feat_run_workflow_from_cli",
                "title": "通过 CLI 运行 workflow",
                "summary": "支持 `lee run` 加载 registry、渲染模板并执行 workflow。",
                "scope": [
                    "解析 workflow key 与 spec 文件。",
                    "触发 create、run_until_blocked 与 summary 输出。",
                ],
                "inputs": ["workflow key", "--spec", "--project-dir"],
                "outputs": ["workflow instance", "rendered template", "execution summary"],
                "business_rules": [
                    "load_spec_as_params 的 workflow 必须把 spec 内容注入 params。",
                    "遇到同 key 运行中 workflow 时要优先恢复或显式重跑。",
                ],
                "acceptance_criteria": [
                    "执行 `lee run core.reverse-epic-feat --spec ...` 可创建并运行实例。",
                    "CLI summary 会输出最终状态与完成步数。",
                ],
                "code_refs": [
                    "src/lee/cli/commands/run.py",
                    "src/lee/cli/main.py",
                ],
            },
            {
                "id": "FEAT-008",
                "key": "feat_query_workflow_status",
                "title": "查询 workflow 状态",
                "summary": "查看 workflow 当前状态、完成步骤与 gate 信息。",
                "scope": [
                    "读取 workflow instance 数据。",
                    "向终端输出状态摘要。",
                ],
                "inputs": ["workflow_id"],
                "outputs": ["status summary"],
                "business_rules": [
                    "状态查询不修改 workflow 数据。",
                    "需要兼容 blocked、paused、failed、completed 等状态。",
                ],
                "acceptance_criteria": [
                    "给定 workflow_id 可以输出当前状态与当前步骤。",
                    "blocked workflow 会显示 gate 指引。",
                ],
                "code_refs": [
                    "src/lee/cli/commands/status.py",
                    "src/lee/cli/main.py",
                ],
            },
            {
                "id": "FEAT-009",
                "key": "feat_approve_human_gates",
                "title": "审批人工门禁",
                "summary": "通过 CLI 审批 gate 并推动 workflow 继续执行。",
                "scope": [
                    "读取 gate id、approver 与审批动作。",
                    "调用 gate API 更新 gate 状态。",
                ],
                "inputs": ["workflow_id", "gate_id", "approver"],
                "outputs": ["approved gate state"],
                "business_rules": [
                    "只有 human gate 允许人工审批。",
                    "审批后 workflow 需可继续推进。",
                ],
                "acceptance_criteria": [
                    "approve 命令能更新 gate 记录。",
                    "审批成功后 workflow 不再停留在原 gate。",
                ],
                "code_refs": [
                    "src/lee/cli/commands/approve.py",
                    "src/lee/orchestrator/execution/gate_api.py",
                ],
            },
        ],
    },
    {
        "id": "CAP-004",
        "name": "SSOT 与治理规则维护",
        "summary": "维护 SSOT contract、spec review 规则与 workflow 模板治理边界。",
        "boundary": "覆盖 SSOT artifact 约束和 review 规则，不包含下游 TECH/TESTSET 派生。",
        "code_refs": [
            "spec-global/core/contracts/ssot-agent-output/v1/schema.json",
            "spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml",
            "spec-global/core/agents/spec-review/v1/agent.yaml",
            "src/lee/cli/commands/ssot.py",
        ],
        "features": [
            {
                "id": "FEAT-010",
                "key": "feat_define_ssot_output_contract",
                "title": "定义 SSOT 输出契约",
                "summary": "使用统一 schema 描述 EPIC/FEAT 等 SSOT 输出对象。",
                "scope": [
                    "约束 key、identity_kind、ssot_type 与关系字段。",
                    "让 materialization 与下游工具共享相同 contract。",
                ],
                "inputs": ["ssot artifact metadata", "content"],
                "outputs": ["contract-compliant ssot-agent-output bundle"],
                "business_rules": [
                    "ssot output 必须声明 ssot_type。",
                    "本 workflow 只允许 epic 与 feat 两种 ssot_type。",
                ],
                "acceptance_criteria": [
                    "生成的 bundle 满足 contract_version=1.0。",
                    "outputs 中只出现 epic/feat 两类 SSOT。",
                ],
                "code_refs": [
                    "spec-global/core/contracts/ssot-agent-output/v1/schema.json",
                    "src/lee/cli/commands/ssot.py",
                ],
            },
            {
                "id": "FEAT-011",
                "key": "feat_enforce_template_instance_boundary",
                "title": "维护模板与实例边界",
                "summary": "在 workflow spec 维护与评审中强制区分 checked-in 模板和 runtime instance。",
                "scope": [
                    "在维护 agent 与 review agent 中加入规则。",
                    "防止 spec 被误描述为运行时实例。",
                ],
                "inputs": ["workflow spec change request", "review context"],
                "outputs": ["template-boundary compliant spec review result"],
                "business_rules": [
                    "checked-in workflow spec 只能描述模板语义。",
                    "运行时 instance 只能在执行阶段动态生成。",
                ],
                "acceptance_criteria": [
                    "workflow spec maintainer 会纠正模板/实例混淆描述。",
                    "spec-review 会将该混淆识别为 review finding。",
                ],
                "code_refs": [
                    "spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml",
                    "spec-global/core/agents/spec-review/v1/agent.yaml",
                ],
            },
        ],
    },
]


def _load_sequence(raw: Optional[str]) -> List[str]:
    if raw is None or raw == "":
        return []
    for loader in (yaml.safe_load, json.loads):
        try:
            value = loader(raw)
            if isinstance(value, list):
                return [str(item) for item in value]
        except Exception:
            continue
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_local_schema(repo_root: Path, relative_path: str) -> Dict[str, Any]:
    schema_path = repo_root / relative_path
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    _ensure_parent(path)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _project_paths(repo_root: Path, specs_dir: str, docs_dir: str, artifacts_dir: str) -> Dict[str, Path]:
    spec_root = repo_root / specs_dir
    requirements_root = spec_root / "requirements"
    docs_root = repo_root / docs_dir
    return {
        "spec_root": spec_root,
        "requirements_root": requirements_root,
        "docs_root": docs_root,
        "guides_root": docs_root / "guides",
        "reports_root": docs_root / "reports",
        "artifacts_root": repo_root / artifacts_dir,
        "artifacts_active_root": (repo_root / artifacts_dir) / "active",
    }


def _repo_relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _include_file(rel_path: str, include_paths: List[str], exclude_paths: List[str]) -> bool:
    normalized = rel_path.replace("\\", "/")
    if any(normalized == item or normalized.startswith(item.rstrip("/") + "/") for item in exclude_paths):
        return False
    if not include_paths:
        return True
    return any(normalized == item or normalized.startswith(item.rstrip("/") + "/") for item in include_paths)


def _collect_files(repo_root: Path, include_paths: List[str], exclude_paths: List[str]) -> List[str]:
    files: List[str] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = _repo_relative(repo_root, path)
        except ValueError:
            continue
        if _include_file(rel, include_paths, exclude_paths):
            files.append(rel)
    return sorted(files)


def _existing_paths(repo_root: Path, rel_paths: Iterable[str]) -> List[str]:
    results: List[str] = []
    for rel in rel_paths:
        if (repo_root / rel).exists():
            results.append(rel)
    return results


def _build_module_summaries(files: List[str]) -> List[Dict[str, Any]]:
    modules = [
        ("requirements", "spec/requirements/", "需求与冻结契约 SSOT"),
        ("legacy_prd", "legacy/spec/prd/", "历史 PRD 与市场分析输入"),
        ("backend", "src/backend/", "后端服务、API、训练与同步实现"),
        ("frontend", "src/frontend/", "前端页面、交互流程与终端集成"),
        ("cli", "src/lee/cli/", "命令行入口与用户操作命令"),
        ("orchestrator", "src/lee/orchestrator/", "工作流编排、执行、状态机与 gate"),
        ("spec_global", "spec-global/", "全局 workflow/agent/contract 模板"),
        ("config", "config/", "工作流与系统配置"),
        ("tests", "tests/", "回归与集成测试"),
        ("scripts", "scripts/", "仓库维护与 workflow 辅助脚本"),
    ]
    summaries: List[Dict[str, Any]] = []
    for key, prefix, summary in modules:
        matched = [item for item in files if item.startswith(prefix)]
        if matched:
            summaries.append({"id": key, "path_prefix": prefix, "summary": summary, "file_count": len(matched)})
    return summaries


def _build_src_index(repo_root: Path, limit: int = 800) -> List[Dict[str, str]]:
    src_root = repo_root / "src"
    if not src_root.exists():
        return []
    indexed: List[Dict[str, str]] = []
    skip_parts = {"node_modules", "blobs", ".git", "dist", "coverage"}
    for path in src_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        if path.suffix.lower() not in SRC_EXTENSIONS:
            continue
        rel = _repo_relative(repo_root, path)
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:4000].lower()
        except Exception:
            content = ""
        indexed.append({"path": rel, "path_lower": rel.lower(), "content": content})
        if len(indexed) >= limit:
            break
    return indexed


def _feature_query_terms(title: str, summary: str, extra: Iterable[str] | None = None) -> List[str]:
    base = f"{title} {summary} {' '.join(extra or [])}".lower()
    tokens = re.findall(r"[a-z0-9_+-]+|[\u4e00-\u9fff]{2,}", base)
    keywords = {
        "对话": ["chat", "dialog", "message", "session", "coach"],
        "意图": ["intent", "parse", "classify"],
        "训练计划": ["plan", "training_plan", "race/plan", "weekly"],
        "训练": ["training", "workout", "session"],
        "复盘": ["review", "summary", "completion", "analysis"],
        "建议": ["advice", "recommend", "suggest"],
        "garmin": ["garmin", "connect", "sync"],
        "apple": ["apple", "healthkit", "watch"],
        "健康": ["health", "heart", "hrv", "rhr"],
        "风险": ["risk", "load", "injury", "warning"],
        "负荷": ["load", "trimp"],
        "订阅": ["subscription", "premium", "purchase"],
        "支付": ["payment", "wechat", "alipay"],
        "登录": ["login", "auth", "wechat"],
        "引导": ["onboarding", "welcome", "profile"],
        "资料": ["profile", "user", "runner"],
        "比赛": ["race", "goal", "marathon"],
        "语音": ["voice", "audio", "tts"],
    }
    expanded = list(tokens)
    for token in list(tokens):
        for key, values in keywords.items():
            if key in token or token in key:
                expanded.extend(values)
    deduped: List[str] = []
    for item in expanded:
        if len(item) < 2:
            continue
        if item not in deduped:
            deduped.append(item)
    return deduped[:20]


def _preferred_onboarding_aliases(title: str, summary: str, terms: Iterable[str]) -> List[str]:
    text = f"{title} {summary} {' '.join(terms)}".lower()
    preferred: List[str] = []
    alias_rules = [
        (("welcome screen", "欢迎页", "welcome"), ["welcome"]),
        (("登录", "注册", "login", "signup", "auth"), ["login"]),
        (("garmin", "佳明", "绑定"), ["garmin-login"]),
        (("基础资料", "资料", "profile", "runner"), ["profile-basic", "runner-profile", "profile"]),
        (("同步", "sync", "初始数据"), ["data-sync", "sync-complete"]),
    ]
    for keys, aliases in alias_rules:
        if any(key in text for key in keys):
            for alias in aliases:
                if alias not in preferred:
                    preferred.append(alias)
    return preferred


def _path_quality_score(path: str) -> int:
    normalized = path.lower()
    score = 0
    strong_signals = [
        "/internal/service/",
        "\\internal\\service\\",
        "/internal/handler/",
        "\\internal\\handler\\",
        "/internal/model/",
        "\\internal\\model\\",
        "/src/pages/",
        "\\src\\pages\\",
        "/src/components/",
        "\\src\\components\\",
        "/src/store/",
        "\\src\\store\\",
        "/src/composables/",
        "\\src\\composables\\",
        "/src/types/",
        "\\src\\types\\",
    ]
    medium_signals = [
        "/internal/repository/",
        "\\internal\\repository\\",
        "/api/",
        "\\api\\",
        "/route",
        "\\route",
        "/router/",
        "\\router\\",
    ]
    weak_signals = [
        "/migrations/",
        "\\migrations\\",
        "/test-cases/e2e-archive/",
        "\\test-cases\\e2e-archive\\",
        "/archive/",
        "\\archive\\",
        "summary",
        "report",
        "output",
        "bug-fix",
        "fix-summary",
        "tmp",
    ]
    for signal in strong_signals:
        if signal in normalized:
            score += 5
    for signal in medium_signals:
        if signal in normalized:
            score += 3
    for signal in weak_signals:
        if signal in normalized:
            score -= 4
    if normalized.endswith(".vue"):
        score += 3
    elif normalized.endswith(".go"):
        score += 2
    elif normalized.endswith((".ts", ".tsx", ".js", ".jsx")):
        score += 1
    elif normalized.endswith(".sql"):
        score -= 2
    return score


def _semantic_path_bonus(path: str, title: str = "", summary: str = "") -> int:
    normalized = path.lower()
    text = f"{title} {summary}".lower()
    score = 0
    alias_groups = {
        "welcome": ["welcome", "onboarding", "intro"],
        "??": ["login", "auth", "signin"],
        "??": ["register", "signup", "auth"],
        "garmin": ["garmin", "connect", "sync-complete"],
        "??": ["bind", "connect", "onboarding"],
        "??": ["profile", "runner", "user"],
        "????": ["body-status", "status", "readiness"],
        "??": ["review", "analysis", "summary"],
        "??": ["race-goal", "race", "goal", "marathon"],
        "??": ["voice", "audio", "tts"],
    }
    negative_groups = {
        "welcome": ["auth-denied", "denied"],
        "??": ["welcome"],
    }
    for key, aliases in alias_groups.items():
        if key in text or any(alias in text for alias in aliases):
            for alias in aliases:
                if alias in normalized:
                    score += 4
    for key, aliases in negative_groups.items():
        if key in text:
            for alias in aliases:
                if alias in normalized:
                    score -= 3
    return score


def _exact_intent_path_bonus(path: str, title: str = "", summary: str = "") -> int:
    normalized = path.lower().replace('\\', '/')
    text = f"{title} {summary}".lower()
    filename = normalized.rsplit('/', 1)[-1]
    stem = filename.rsplit('.', 1)[0]
    parent = normalized.rsplit('/', 2)[-2] if '/' in normalized else ''
    score = 0
    intent_aliases = {
        "???": ["welcome"],
        "welcome": ["welcome"],
        "??": ["login"],
        "??": ["login", "signup", "register"],
        "garmin": ["garmin-login", "garmin", "connect"],
        "??": ["garmin-login", "connect", "bind"],
        "????": ["profile-basic", "profile", "runner-profile"],
        "??": ["profile-basic", "profile", "runner-profile"],
        "??????": ["data-sync", "sync-complete", "sync"],
        "????": ["data-sync", "sync-complete", "sync"],
        "????": ["body-status-input", "body-status", "status"],
        "????": ["race-goal", "plan-goal", "goal"],
        "????": ["race-plan", "plan-goal", "race-goal"],
        "??": ["race-summary", "review", "summary"],
        "??": ["voice", "audio", "tts"],
    }
    for key, aliases in intent_aliases.items():
        if key in text:
            for alias in aliases:
                if stem == alias or parent == alias:
                    score += 10
                elif alias in stem or alias in parent:
                    score += 6
    if "???" in text and "welcome" in normalized:
        score += 8
    if "???" in text and ("garmin-login" in normalized or "data-sync" in normalized):
        score -= 8
    if "???" in text and "/login" in normalized:
        score -= 3
    if "garmin" in text and "welcome" in normalized:
        score -= 2
    return score


def _page_content_bonus(content: str, path: str, title: str = "", summary: str = "") -> int:
    text = f"{title} {summary}".lower()
    normalized = path.lower().replace("\\", "/")
    lowered = (content or "").lower()
    score = 0
    if "欢迎页" in text or "welcome" in text:
        if "欢迎页" in lowered or "welcome-page" in lowered:
            score += 12
        if "开始使用" in lowered or "app-slogan" in lowered or "logo-section" in lowered:
            score += 8
        if "验证码" in lowered or "手机号" in lowered or "verify-code" in lowered:
            score -= 6
        if "garmin" in lowered and "connect garmin" in lowered:
            score -= 4
    if "登录" in text or "注册" in text or "login" in text:
        if "登录/注册" in lowered or "请输入手机号完成登录或注册" in lowered:
            score += 12
        if "验证码" in lowered or "手机号" in lowered:
            score += 8
        if "欢迎页" in lowered and "开始使用" in lowered:
            score -= 4
    if "garmin" in text or "绑定" in text:
        if "connect garmin" in lowered or "连接 garmin" in lowered or "garmin oauth" in lowered:
            score += 12
        if "sync-complete" in normalized or "data-sync" in normalized:
            score += 4
        if "欢迎页" in lowered and "开始使用" in lowered:
            score -= 4
    if "资料" in text or "profile" in text:
        if "完善你的基本信息" in lowered or "profile-basic" in normalized:
            score += 10
    return score


def _find_src_refs(index: List[Dict[str, str]], terms: List[str], limit: int = 5, title: str = "", summary: str = "") -> List[str]:
    scored: List[Tuple[int, str]] = []
    for entry in index:
        score = 0
        for term in terms:
            if term in entry["path_lower"]:
                score += 3
            if term in entry["content"]:
                score += 1
        if score > 0:
            total_score = score + _path_quality_score(entry["path"]) + _semantic_path_bonus(entry["path"], title=title, summary=summary) + _exact_intent_path_bonus(entry["path"], title=title, summary=summary) + _page_content_bonus(entry.get("content", ""), entry["path"], title=title, summary=summary)
            scored.append((total_score, entry["path"]))
    scored.sort(key=lambda item: (-item[0], item[1]))
    results: List[str] = []
    for _, path in scored:
        if path not in results:
            results.append(path)
        if len(results) >= limit:
            break
    onboarding_candidates = [path for path in results if "/pages/onboarding/" in path.replace("\\", "/").lower()]
    if onboarding_candidates:
        preferred_aliases = _preferred_onboarding_aliases(title, summary, terms)
        if preferred_aliases:
            def _onboarding_rank(path: str) -> Tuple[int, int, str]:
                normalized = path.replace("\\", "/").lower()
                filename = normalized.rsplit("/", 1)[-1]
                stem = filename.rsplit(".", 1)[0]
                exact = 0 if any(stem == alias for alias in preferred_aliases) else 1
                partial = 0 if any(alias in stem for alias in preferred_aliases) else 1
                return (exact, partial, normalized)

            ordered: List[str] = []
            prioritized = sorted(onboarding_candidates, key=_onboarding_rank)
            for path in prioritized + results:
                if path not in ordered:
                    ordered.append(path)
            results = ordered[:limit]
    return results


def _classify_ref(path: str) -> str:
    normalized = path.lower()
    if normalized.startswith("spec/") or normalized.startswith("legacy/spec/"):
        return "doc"
    if "/test" in normalized or "\\test" in normalized or "spec.ts" in normalized or "_test." in normalized or normalized.endswith("test.go"):
        return "test"
    if "api" in normalized or "/handler/" in normalized or "\\handler\\" in normalized or "/route" in normalized or "\\route" in normalized or "pages.json" in normalized:
        return "api"
    if normalized.endswith(".md"):
        return "doc"
    if normalized.endswith((".json", ".yaml", ".yml")) and ("/docs/" in normalized or "\\docs\\" in normalized):
        return "doc"
    return "impl"


def _build_evidence_layers(refs: Iterable[str]) -> Dict[str, List[str]]:
    layers: Dict[str, List[str]] = {"impl_refs": [], "api_refs": [], "test_refs": [], "doc_refs": []}
    for ref in refs:
        bucket = _classify_ref(ref)
        key = {
            "impl": "impl_refs",
            "api": "api_refs",
            "test": "test_refs",
            "doc": "doc_refs",
        }[bucket]
        if ref not in layers[key]:
            layers[key].append(ref)
    return layers


def _sort_refs_by_quality(refs: Iterable[str]) -> List[str]:
    return sorted(dict.fromkeys(refs), key=lambda item: (-_path_quality_score(item), item))


def _primary_refs_from_layers(layers: Dict[str, List[str]], limit: int = 8) -> List[str]:
    ordered: List[str] = []
    preferred_keys = ("impl_refs", "api_refs")
    fallback_keys = ("doc_refs", "test_refs")
    keys = preferred_keys if any(layers.get(key) for key in preferred_keys) else fallback_keys
    for key in keys:
        for ref in _sort_refs_by_quality(layers.get(key, [])):
            if ref not in ordered:
                ordered.append(ref)
            if len(ordered) >= limit:
                return ordered
    return ordered


def _primary_refs_from_ordered_refs(refs: Iterable[str], limit: int = 8) -> List[str]:
    ordered: List[str] = []
    impl_or_api: List[str] = []
    fallback: List[str] = []
    for ref in dict.fromkeys(refs):
        ref_class = _classify_ref(ref)
        if ref_class in {"impl", "api"}:
            impl_or_api.append(ref)
        else:
            fallback.append(ref)
    source = impl_or_api if impl_or_api else fallback
    for ref in source:
        if ref not in ordered:
            ordered.append(ref)
        if len(ordered) >= limit:
            break
    return ordered


def _load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", text.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "item"


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _strip_markdown_prefix(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^#+\s*", "", cleaned)
    cleaned = re.sub(r"^\*\*([^*]+)\*\*[:：]?\s*", "", cleaned)
    cleaned = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+|\(\d+\)\s*)", "", cleaned)
    return _normalize_spaces(cleaned)


def _looks_like_diagram_or_table(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    if stripped.startswith("|") and stripped.endswith("|"):
        return True
    if re.fullmatch(r"[\|\-\+\=\s]+", stripped):
        return True
    if any(token in stripped for token in ("┌", "┐", "└", "┘", "├", "┤", "│", "─")):
        return True
    return False


def _is_meaningful_text(text: str) -> bool:
    cleaned = _strip_markdown_prefix(text)
    if not cleaned:
        return False
    if _looks_like_diagram_or_table(cleaned):
        return False
    if cleaned in {"---", "```"}:
        return False
    return True


def _clean_summary_text(text: str, fallback: str) -> str:
    cleaned = _strip_markdown_prefix(text)
    if not _is_meaningful_text(cleaned):
        cleaned = _strip_markdown_prefix(fallback)
    return cleaned or _normalize_spaces(fallback) or "未命名功能"


def _choose_best_summary(primary: str, fallback: str, supporting_items: Optional[Iterable[str]] = None) -> str:
    candidates = [_clean_summary_text(primary, fallback), _clean_summary_text(fallback, primary)]
    for item in supporting_items or []:
        cleaned = _clean_summary_text(item, "")
        if cleaned:
            candidates.append(cleaned)
    for candidate in candidates:
        if not candidate:
            continue
        if len(candidate) >= 8:
            return candidate
    return next((candidate for candidate in candidates if candidate), "未命名功能")


def _clean_list_items(items: Iterable[str], fallback: Optional[str] = None) -> List[str]:
    cleaned_items: List[str] = []
    for item in items:
        cleaned = _clean_summary_text(item, "")
        if cleaned and cleaned not in cleaned_items:
            cleaned_items.append(cleaned)
    if cleaned_items:
        return cleaned_items
    if fallback:
        fallback_cleaned = _clean_summary_text(fallback, "")
        if fallback_cleaned:
            return [fallback_cleaned]
    return []


def _derive_preconditions(feature: Dict[str, Any]) -> List[str]:
    defaults: List[str] = []
    if feature.get("inputs"):
        defaults.append(f"上游已提供完成该能力所需输入：{'、'.join(feature['inputs'][:3])}。")
    defaults.append("相关代码路径和基础配置已存在且可访问；若依赖数据缺失，则必须进入显式降级路径。")
    return _clean_list_items(feature.get("preconditions") or defaults, defaults[0])


def _derive_main_flow(feature: Dict[str, Any]) -> List[str]:
    title = feature.get("title", "该功能")
    summary = feature.get("summary", title)
    business_rules = feature.get("business_rules") or []
    outputs = feature.get("outputs") or ["业务结果"]
    defaults = [
        f"触发 {title} 后，系统读取并校验所需输入，进入 {summary} 对应处理流程。",
        f"处理过程中应用核心业务规则：{business_rules[0] if business_rules else '按冻结需求与现有实现约束执行。'}",
        f"完成后输出并落库/回传：{'、'.join(outputs[:3])}。",
    ]
    return _clean_list_items(feature.get("main_flow") or defaults, defaults[0])


def _derive_edge_cases(feature: Dict[str, Any]) -> List[str]:
    title = feature.get("title", "该功能")
    inputs = feature.get("inputs") or ["关键输入"]
    defaults = [
        f"当 {inputs[0]} 缺失、非法或超出合理范围时，系统必须阻止错误结果落地并给出明确反馈。",
        f"当 {title} 所依赖的实时数据、外部同步或历史记录不足时，系统必须走降级策略而不是静默生成默认结果。",
    ]
    return _clean_list_items(feature.get("edge_cases") or defaults, defaults[0])


def _derive_state_updates(feature: Dict[str, Any]) -> List[str]:
    outputs = feature.get("outputs") or ["状态更新"]
    defaults = [
        f"成功执行后更新相关业务状态：{'、'.join(outputs[:3])}。",
        "若进入降级、失败或待人工处理路径，必须保留可追踪的状态标记与原因。",
    ]
    return _clean_list_items(feature.get("state_updates") or defaults, defaults[0])


def _derive_goal(feature: Dict[str, Any]) -> str:
    return _clean_summary_text(feature.get("goal", "") or feature.get("summary", "") or feature.get("title", ""), feature.get("title", "未命名功能"))


def _derive_user_value(feature: Dict[str, Any]) -> str:
    title = feature.get("title", "该功能")
    outputs = feature.get("outputs") or ["业务结果"]
    fallback = f"用户可以获得 {outputs[0]}，并完成 {title} 对应业务目标。"
    return _clean_summary_text(feature.get("user_value", "") or fallback, fallback)


def _derive_processing(feature: Dict[str, Any]) -> List[str]:
    defaults = list(feature.get("main_flow") or [])
    if not defaults:
        defaults = [f"根据输入和业务规则执行 {feature.get('title', '该功能')}。"]
    return _clean_list_items(feature.get("processing") or defaults, defaults[0])


def _derive_dependencies(feature: Dict[str, Any], capability: Optional[Dict[str, Any]] = None) -> List[str]:
    defaults: List[str] = []
    if capability:
        defaults.append(capability["id"])
    inputs = feature.get("inputs") or []
    if inputs:
        defaults.append(f"依赖上游提供：{'、'.join(inputs[:2])}")
    return _clean_list_items(feature.get("dependencies") or defaults)


def _derive_non_goals(feature: Dict[str, Any]) -> List[str]:
    defaults = list(feature.get("scope", [])[1:2]) or ["不包含下游 UI、TECH、TASK、TESTSET 派生设计本身。"]
    return _clean_list_items(feature.get("non_goals") or defaults, defaults[0])


def _derive_acceptance_checks(feature: Dict[str, Any]) -> List[Dict[str, Any]]:
    existing = feature.get("acceptance_checks") or []
    if existing:
        return existing
    checks: List[Dict[str, Any]] = []
    title = feature.get("title", "该功能")
    inputs = feature.get("inputs") or ["必要输入"]
    outputs = feature.get("outputs") or ["业务结果"]
    edge_cases = feature.get("edge_cases") or ["依赖数据不足时进入降级处理。"]
    for index, item in enumerate(feature.get("acceptance_criteria") or [], start=1):
        check_id = f"AC-{index:03d}"
        if index == 1:
            given = f"已满足前置条件，且提供 {inputs[0]}。"
            when = f"触发 {title} 主流程。"
            then = item
            trace_hints = ["TASK", "TESTSET", "UI", "TECH"]
        else:
            given = f"系统处于 {title} 处理中，且相关规则已生效。"
            when = f"执行与 {item} 对应的业务步骤。"
            then = f"系统应输出/更新：{outputs[min(index - 1, len(outputs) - 1)] if outputs else item}"
            trace_hints = ["TASK", "TESTSET", "TECH"]
        checks.append(
            {
                "id": check_id,
                "scenario": item,
                "given": given,
                "when": when,
                "then": then,
                "trace_hints": trace_hints,
            }
        )
    if len(checks) < 2:
        fallback_checks = [
            {
                "id": "AC-001",
                "scenario": f"{title} 正常主流程可完成",
                "given": f"已提供 {inputs[0]}。",
                "when": f"执行 {title} 主流程。",
                "then": f"系统应输出 {outputs[0]}。",
                "trace_hints": ["TASK", "TESTSET", "UI", "TECH"],
            },
            {
                "id": "AC-002",
                "scenario": f"{title} 异常/边界场景可被正确处理",
                "given": edge_cases[0],
                "when": f"执行 {title} 时命中异常或边界条件。",
                "then": "系统应给出明确反馈，并保留正确状态标记。",
                "trace_hints": ["TASK", "TESTSET", "TECH"],
            },
        ]
        checks = fallback_checks
    return checks


def _enrich_feature_detail(feature: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(feature)
    enriched["preconditions"] = _derive_preconditions(enriched)
    enriched["main_flow"] = _derive_main_flow(enriched)
    enriched["edge_cases"] = _derive_edge_cases(enriched)
    enriched["state_updates"] = _derive_state_updates(enriched)
    enriched["goal"] = _derive_goal(enriched)
    enriched["user_value"] = _derive_user_value(enriched)
    enriched["processing"] = _derive_processing(enriched)
    enriched["dependencies"] = _derive_dependencies(enriched)
    enriched["non_goals"] = _derive_non_goals(enriched)
    enriched["priority"] = enriched.get("priority", "P1")
    enriched["delivery_slice"] = enriched.get("delivery_slice", "reverse-draft")
    enriched["lifecycle_status"] = enriched.get("lifecycle_status", "draft")
    enriched["derived_object_expectations"] = enriched.get(
        "derived_object_expectations",
        {
            "task_required": True,
            "testset_required": True,
            "testset_owner": "qa",
            "qa_seed_required": True,
        },
    )
    enriched["business_rules"] = _clean_list_items(enriched.get("business_rules") or [], "以冻结需求与现有实现约束为准。")
    enriched["acceptance_criteria"] = _clean_list_items(enriched.get("acceptance_criteria") or [], "具备独立验收条件。")
    enriched["acceptance_checks"] = _derive_acceptance_checks(enriched)
    return enriched


def _enrich_feature_with_context(feature: Dict[str, Any], capability: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    enriched = _enrich_feature_detail(feature)
    enriched["dependencies"] = _derive_dependencies(enriched, capability=capability)
    return enriched


def _extract_labeled_value(line: str, label: str) -> Optional[str]:
    pattern = rf"^\*\*{re.escape(label)}\*\*[:：]?\s*(.+)$"
    match = re.match(pattern, line.strip())
    if not match:
        return None
    value = _normalize_spaces(match.group(1))
    return value or None


def _has_markdown_section(content: str, heading: str) -> bool:
    target = f"## {heading}".lower()
    return any(line.strip().lower() == target for line in (content or "").splitlines())


def _count_section_bullets(content: str, heading: str) -> int:
    lines = (content or "").splitlines()
    capture = False
    count = 0
    for line in lines:
        if line.strip().lower() == f"## {heading}".lower():
            capture = True
            continue
        if capture and line.strip().startswith("## "):
            break
        if capture and line.strip().startswith("- "):
            count += 1
    return count


def _count_acceptance_check_blocks(content: str) -> int:
    lines = (content or "").splitlines()
    capture = False
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.lower() == "## acceptance checks":
            capture = True
            continue
        if capture and stripped.startswith("## "):
            break
        if capture and stripped.startswith("### "):
            count += 1
    return count


def _extract_markdown_feature_sections(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for line in lines:
        if line.startswith("### "):
            if current:
                sections.append(current)
            title = line[4:].strip()
            current = {"title": title, "lines": []}
            continue
        if current is not None:
            current["lines"].append(line)
    if current:
        sections.append(current)

    results: List[Dict[str, Any]] = []
    for section in sections:
        title = section["title"]
        if not re.search(r"(^F[\w-]*\d)|(^FEAT[\w-]*)", title, re.IGNORECASE):
            continue
        body_lines: List[str] = section["lines"]
        description = ""
        business_rules: List[str] = []
        acceptance: List[str] = []
        current_bucket: Optional[List[str]] = None
        expect_description = False
        for raw in body_lines:
            line = raw.strip()
            inline_description = _extract_labeled_value(line, "描述")
            if inline_description:
                description = _clean_summary_text(inline_description, title)
                expect_description = False
                current_bucket = None
                continue
            if line.startswith("**描述**"):
                expect_description = True
                current_bucket = None
                continue
            if expect_description:
                if _is_meaningful_text(line) and not line.startswith("**") and not line.startswith("```") and not line.startswith("|"):
                    description = _clean_summary_text(line, title)
                    expect_description = False
                    continue
                if line:
                    expect_description = False
            if line.startswith("**业务规则**"):
                current_bucket = business_rules
                continue
            if line.startswith("**验收标准**"):
                current_bucket = acceptance
                continue
            if line.startswith("**") and line.endswith("**"):
                current_bucket = None
                continue
            if line.startswith("- ") or line.startswith("[ ]") or line.startswith("- [ ]") or line.startswith("[ ]"):
                cleaned = line.replace("- [ ]", "").replace("[ ]", "").replace("- ", "").strip()
                if current_bucket is not None and _is_meaningful_text(cleaned):
                    current_bucket.append(cleaned)
                continue
            if not description and _is_meaningful_text(line) and not line.startswith("**") and not line.startswith("```") and not line.startswith("|"):
                description = _clean_summary_text(line, title)
        results.append(
            {
                "id": _slugify(title)[:32],
                "name": _clean_summary_text(title, "未命名功能"),
                "description": _clean_summary_text(description or title, title),
                "business_rules": _clean_list_items(business_rules),
                "acceptance_criteria": _clean_list_items(acceptance),
                "source_ref": path.as_posix(),
            }
        )
    return results


def _build_doc_derived_capabilities(repo_root: Path, max_capabilities: int, max_features: int) -> List[Dict[str, Any]]:
    capabilities: List[Dict[str, Any]] = []
    src_index = _build_src_index(repo_root)
    requirements_root = repo_root / "spec" / "requirements"
    legacy_prd_root = repo_root / "legacy" / "spec" / "prd"
    module_requirements_path = requirements_root / "module-requirements.json"
    detailed_prd_path = requirements_root / "prd-detailed.json"
    onboarding_prd_path = legacy_prd_root / "v1.2-onboarding-prd-simplified.md"

    module_requirements = _load_json_file(module_requirements_path) or {}
    detailed_prd = _load_json_file(detailed_prd_path) or {}

    detailed_features = (detailed_prd.get("functional_details") or {}).get("features", [])
    freeze_requirements_path = requirements_root / "requirements-frozen.md"
    onboarding_features = _extract_markdown_feature_sections(onboarding_prd_path)[:max_features]

    if onboarding_features:
        capabilities.append(
            {
                "id": "CAP-ONB",
                "name": "新用户引导与设备绑定",
                "summary": "基于 onboarding PRD 抽取的首次使用、资料录入、手表绑定和初始同步能力。",
                "boundary": "覆盖欢迎页、注册、基础资料、手表绑定和首次同步，不含后续训练编排。",
                "code_refs": [
                    _repo_relative(repo_root, onboarding_prd_path),
                    _repo_relative(repo_root, freeze_requirements_path) if freeze_requirements_path.exists() else _repo_relative(repo_root, onboarding_prd_path),
                ],
                "features": [
                    {
                        "id": feature["id"],
                        "key": f"feat_{_slugify(feature['name'])[:40]}",
                        "title": _clean_summary_text(feature["name"], "未命名功能"),
                        "summary": _choose_best_summary(feature["description"], feature["name"], feature["business_rules"]),
                        "scope": [_choose_best_summary(feature["description"], feature["name"], feature["business_rules"])],
                        "inputs": ["用户输入", "设备授权", "历史训练数据"],
                        "outputs": ["引导状态更新", "绑定结果", "初始同步结果"],
                        "business_rules": _clean_list_items(feature["business_rules"], "以 onboarding PRD 中定义的流程和校验为准。"),
                        "acceptance_criteria": _clean_list_items(feature["acceptance_criteria"], "具备独立验收条件。"),
                        **(lambda all_refs: {
                            "all_refs": all_refs,
                            "evidence_layers": _build_evidence_layers(all_refs),
                            "code_refs": _primary_refs_from_ordered_refs(all_refs),
                        })(
                            list(
                                dict.fromkeys(
                                    [_repo_relative(repo_root, onboarding_prd_path)]
                                    + _find_src_refs(
                                        src_index,
                                        _feature_query_terms(
                                            _clean_summary_text(feature["name"], "未命名功能"),
                                            _choose_best_summary(feature["description"], feature["name"], feature["business_rules"]),
                                            _clean_list_items(feature["business_rules"]),
                                        ),
                                        title=_clean_summary_text(feature["name"], "未命名功能"),
                                        summary=_choose_best_summary(feature["description"], feature["name"], feature["business_rules"]),
                                    )
                                )
                            )
                        ),
                    }
                    for feature in onboarding_features
                ],
            }
        )

    module_keyword_map = {
        "AI对话模块": ["对话", "意图", "AI"],
        "自适应训练计划模块": ["身体状态", "动态调整", "计划", "比赛目标"],
        "训练建议与复盘模块": ["训练前", "训练后", "复盘", "建议"],
        "手表数据对接模块": ["Garmin", "Apple Watch", "HealthKit", "数据对接", "同步"],
        "损伤风险预警模块": ["损伤", "风险", "负荷"],
        "语音指导模块": ["语音", "播报"],
        "订阅支付模块": ["订阅", "支付", "免费", "付费"],
        "比赛目标设定模块": ["比赛目标", "备赛", "半马", "全马"],
    }

    modules = ((module_requirements.get("module_definitions") or {}).get("modules") or [])[:max_capabilities]
    feature_best_module: Dict[str, Tuple[str, int]] = {}
    for feature in detailed_features:
        feature_id = feature.get("id")
        if not feature_id:
            continue
        text = f"{feature.get('name', '')} {feature.get('description', '')}"
        best_module_id = ""
        best_score = 0
        for module in modules:
            module_name = module.get("name", "")
            keywords = module_keyword_map.get(module_name, [module_name[:4], module_name[-4:]])
            score = sum(2 for keyword in keywords if keyword and keyword in text)
            if score > best_score:
                best_score = score
                best_module_id = module.get("id", "")
        if best_module_id and best_score > 0:
            feature_best_module[feature_id] = (best_module_id, best_score)

    for module in modules:
        if len(capabilities) >= max_capabilities:
            break
        module_name = module.get("name", "")
        module_summary = _choose_best_summary(module.get("description", module_name), module_name, [module.get("boundaries", "")])
        module_boundary = _clean_summary_text(module.get("boundaries", "以模块定义边界为准。"), "以模块定义边界为准。")
        matched = []
        for feature in detailed_features:
            assignment = feature_best_module.get(feature.get("id", ""))
            if assignment and assignment[0] == module.get("id"):
                matched.append(feature)
        matched = matched[:max_features]
        features = []
        for feature in matched:
            raw_name = feature.get("name", "未命名功能")
            raw_description = feature.get("description", module_summary)
            clean_name = _clean_summary_text(raw_name, "未命名功能")
            clean_summary = _choose_best_summary(raw_description, clean_name, feature.get("business_rules") or [])
            clean_business_rules = _clean_list_items(feature.get("business_rules") or [], "以冻结需求与详细 PRD 为准。")
            clean_acceptance = _clean_list_items(feature.get("acceptance_criteria") or [], "具备独立验收条件。")
            feature_refs = [_repo_relative(repo_root, module_requirements_path), _repo_relative(repo_root, detailed_prd_path)]
            if freeze_requirements_path.exists():
                feature_refs.append(_repo_relative(repo_root, freeze_requirements_path))
            feature_refs.extend(_find_src_refs(src_index, _feature_query_terms(clean_name, clean_summary, clean_business_rules), title=clean_name, summary=clean_summary))
            feature_refs = list(dict.fromkeys(feature_refs))
            evidence_layers = _build_evidence_layers(feature_refs)
            features.append(
                {
                    "id": feature.get("id", _slugify(feature.get("name", "feature"))[:32]),
                    "key": f"feat_{_slugify(feature.get('id', feature.get('name', 'feature')))[:40]}",
                    "title": clean_name,
                    "summary": clean_summary,
                    "scope": [clean_summary],
                    "inputs": ["用户输入", "训练记录", "手表同步数据"],
                    "outputs": ["训练建议", "分析结果", "状态更新"],
                    "business_rules": clean_business_rules,
                    "acceptance_criteria": clean_acceptance,
                    "all_refs": feature_refs,
                    "evidence_layers": evidence_layers,
                    "code_refs": _primary_refs_from_ordered_refs(feature_refs),
                }
            )
        if not features:
            feature_refs = [_repo_relative(repo_root, module_requirements_path)]
            if freeze_requirements_path.exists():
                feature_refs.append(_repo_relative(repo_root, freeze_requirements_path))
            feature_refs.extend(_find_src_refs(src_index, _feature_query_terms(module_name, module_summary, [module_boundary]), title=module_name, summary=module_summary))
            feature_refs = list(dict.fromkeys(feature_refs))
            evidence_layers = _build_evidence_layers(feature_refs)
            features.append(
                {
                    "id": module.get("id", _slugify(module_name)[:32]),
                    "key": f"feat_{_slugify(module_name)[:40]}",
                    "title": _clean_summary_text(module_name, "未命名功能"),
                    "summary": module_summary,
                    "scope": [module_summary],
                    "inputs": ["用户输入", "上游模块数据"],
                    "outputs": ["模块级业务结果"],
                    "business_rules": [module_boundary],
                    "acceptance_criteria": ["模块定义中的目标能力可独立验收。"],
                    "all_refs": feature_refs,
                    "evidence_layers": evidence_layers,
                    "code_refs": _primary_refs_from_ordered_refs(feature_refs),
                }
            )
        capabilities.append(
            {
                "id": module.get("id", _slugify(module_name)[:32]),
                "name": module_name,
                "summary": module_summary,
                "boundary": module_boundary,
                "code_refs": list(
                    dict.fromkeys(
                        [_repo_relative(repo_root, module_requirements_path), _repo_relative(repo_root, detailed_prd_path)]
                        + _find_src_refs(src_index, _feature_query_terms(module_name, module_summary, [module_boundary]), title=module_name, summary=module_summary)
                    )
                ),
                "features": features[:max_features],
            }
        )

    return capabilities[:max_capabilities]


def run_scan(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    paths = _project_paths(repo_root, args.specs_dir, args.docs_dir, args.artifacts_dir)
    include_paths = _load_sequence(args.include_paths)
    exclude_paths = _load_sequence(args.exclude_paths)
    files = _collect_files(repo_root, include_paths, exclude_paths)
    py_files = [item for item in files if item.endswith(".py")]
    yaml_files = [item for item in files if item.endswith((".yaml", ".yml"))]
    md_files = [item for item in files if item.endswith(".md")]
    cli_commands = sorted([Path(item).stem for item in files if item.startswith("src/lee/cli/commands/") and item.endswith(".py") and not item.endswith("__init__.py")])
    workflow_templates = sorted([item for item in files if "workflows/" in item and item.endswith((".yaml", ".yml"))])
    summary = {
        "repository_summary": {
            "name": repo_root.name,
            "generated_at": _utc_now(),
            "include_paths": include_paths,
            "exclude_paths": exclude_paths,
            "top_level_entries": sorted([item.name for item in repo_root.iterdir()]),
            "statistics": {
                "files": len(files),
                "python_files": len(py_files),
                "yaml_files": len(yaml_files),
                "markdown_files": len(md_files),
                "workflow_templates": len(workflow_templates),
                "cli_commands": len(cli_commands),
            },
            "modules": _build_module_summaries(files),
            "cli_commands": cli_commands,
            "workflow_templates": workflow_templates[:40],
        }
    }
    fixed_refs = [
        "README.md",
        "config/workflow-registry.yaml",
        "src/lee/cli/commands/run.py",
        "src/lee/orchestrator/execution/template_manager.py",
        "src/lee/orchestrator/execution/orchestrator.py",
        "src/lee/orchestrator/execution/state_machine.py",
        "src/lee/orchestrator/execution/runners/auto_check_gate_runner.py",
        "src/lee/orchestrator/execution/runners/shell_runner.py",
        "spec-global/core/contracts/ssot-agent-output/v1/schema.json",
        "spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml",
        "spec-global/core/agents/spec-review/v1/agent.yaml",
    ]
    evidence = []
    for index, rel_path in enumerate(fixed_refs, start=1):
        if (repo_root / rel_path).exists():
            evidence.append({"id": f"EVID-{index:03d}", "type": "code" if rel_path.endswith((".py", ".json", ".yaml")) else "documentation", "file_path": rel_path, "status": "verified", "captured_at": _utc_now()})
    _write_json(paths["reports_root"] / "repo-summary.json", summary)
    _write_json(paths["reports_root"] / "evidence-index.json", {"evidence_index": evidence, "generated_at": _utc_now()})
    print(json.dumps({"repo_file_count": len(files), "evidence_count": len(evidence)}, ensure_ascii=False))
    return 0


def run_system_map(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    paths = _project_paths(repo_root, args.specs_dir, args.docs_dir, args.artifacts_dir)
    repo_summary = json.loads((paths["reports_root"] / "repo-summary.json").read_text(encoding="utf-8"))
    evidence_index = json.loads((paths["reports_root"] / "evidence-index.json").read_text(encoding="utf-8"))
    modules = repo_summary["repository_summary"].get("modules", [])
    system_map = {
        "generated_at": _utc_now(),
        "system_name": repo_root.name,
        "modules": [{"name": item["id"], "path_prefix": item["path_prefix"], "responsibility": item["summary"]} for item in modules],
        "entry_points": {
            "cli_commands": repo_summary["repository_summary"].get("cli_commands", [])[:20],
            "workflow_registry": "config/workflow-registry.yaml",
            "workflow_templates": repo_summary["repository_summary"].get("workflow_templates", [])[:10],
        },
        "core_flows": [
            {"name": "Workflow Run Flow", "steps": ["CLI loads workflow registry", "run.py renders workflow template", "template_manager parses rendered workflow", "orchestrator schedules steps and gates"]},
            {"name": "Spec Governance Flow", "steps": ["workflow spec maintainer updates spec templates", "spec-review validates governance rules", "SSOT contracts constrain generated artifacts"]},
        ],
        "evidence_refs": [item["file_path"] for item in evidence_index.get("evidence_index", [])],
    }
    md_lines = ["# System Map", "", f"- System: `{repo_root.name}`", f"- Generated At: `{system_map['generated_at']}`", "", "## Modules", ""]
    for item in system_map["modules"]:
        md_lines.extend([f"### {item['name']}", f"- Path Prefix: `{item['path_prefix']}`", f"- Responsibility: {item['responsibility']}", ""])
    md_lines.extend(["## Entry Points", "", f"- Workflow Registry: `{system_map['entry_points']['workflow_registry']}`", "- CLI Commands:"])
    for command in system_map["entry_points"]["cli_commands"][:10]:
        md_lines.append(f"  - `{command}`")
    md_lines.append("- Workflow Templates:")
    for template in system_map["entry_points"]["workflow_templates"][:8]:
        md_lines.append(f"  - `{template}`")
    md_lines.extend(["", "## Core Flows", ""])
    for flow in system_map["core_flows"]:
        md_lines.append(f"### {flow['name']}")
        for step in flow["steps"]:
            md_lines.append(f"- {step}")
        md_lines.append("")
    md_lines.extend(["## Evidence Refs", ""])
    for ref in system_map["evidence_refs"]:
        md_lines.append(f"- `{ref}`")
    _write_text(paths["guides_root"] / "system-map.md", "\n".join(md_lines))
    _write_json(paths["reports_root"] / "system-map.json", system_map)
    print(json.dumps({"module_count": len(system_map["modules"])}, ensure_ascii=False))
    return 0


def _selected_capabilities(repo_root: Path, max_capabilities: int, max_features: int) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = _build_doc_derived_capabilities(repo_root, max_capabilities, max_features)
    if selected:
        for capability in selected:
            capability["features"] = [_enrich_feature_with_context(feature, capability=capability) for feature in capability.get("features", [])[:max_features]]
        return selected[:max_capabilities]

    selected = []
    for capability in CANDIDATE_CAPABILITIES:
        code_refs = _existing_paths(repo_root, capability["code_refs"])
        if not code_refs:
            continue
        cloned = {"id": capability["id"], "name": capability["name"], "summary": capability["summary"], "boundary": capability["boundary"], "code_refs": code_refs, "features": []}
        for feature in capability["features"][:max_features]:
            feature_code_refs = _existing_paths(repo_root, feature["code_refs"])
            if feature_code_refs:
                cloned["features"].append(_enrich_feature_with_context({**feature, "code_refs": feature_code_refs}, capability=cloned))
        if cloned["features"]:
            selected.append(cloned)
        if len(selected) >= max_capabilities:
            break
    return selected


def run_capability_map(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    paths = _project_paths(repo_root, args.specs_dir, args.docs_dir, args.artifacts_dir)
    capabilities = _selected_capabilities(repo_root, args.max_capabilities, args.max_features_per_capability)
    payload_capabilities = []
    for item in capabilities:
        evidence_layers = _build_evidence_layers(item["code_refs"])
        payload_capabilities.append(
            {
                "id": item["id"],
                "name": item["name"],
                "summary": item["summary"],
                "boundary": item["boundary"],
                "primary_refs": _primary_refs_from_layers(evidence_layers),
                "evidence_refs": item["code_refs"],
                "evidence_layers": evidence_layers,
            }
        )
    payload = {"generated_at": _utc_now(), "capabilities": payload_capabilities}
    md_lines = ["# Capability Map", "", f"- Generated At: `{payload['generated_at']}`", ""]
    for item in payload["capabilities"]:
        md_lines.extend([f"## {item['id']} {item['name']}", f"- Summary: {item['summary']}", f"- Boundary: {item['boundary']}", "- Primary Refs:"])
        for ref in item["primary_refs"]:
            md_lines.append(f"  - `{ref}`")
        md_lines.extend(["- Evidence Layers:", "  - Impl Refs:"])
        for ref in item["evidence_layers"]["impl_refs"]:
            md_lines.append(f"    - `{ref}`")
        md_lines.append("  - API Refs:")
        for ref in item["evidence_layers"]["api_refs"]:
            md_lines.append(f"    - `{ref}`")
        md_lines.append("  - Test Refs:")
        for ref in item["evidence_layers"]["test_refs"]:
            md_lines.append(f"    - `{ref}`")
        md_lines.append("  - Doc Refs:")
        for ref in item["evidence_layers"]["doc_refs"]:
            md_lines.append(f"    - `{ref}`")
        md_lines.append("- Evidence Refs:")
        for ref in item["evidence_refs"]:
            md_lines.append(f"  - `{ref}`")
        md_lines.append("")
    _write_text(paths["guides_root"] / "capability-map.md", "\n".join(md_lines))
    _write_json(paths["reports_root"] / "capability-map.json", payload)
    print(json.dumps({"capability_count": len(payload["capabilities"])}, ensure_ascii=False))
    return 0


def run_feature_registry(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    paths = _project_paths(repo_root, args.specs_dir, args.docs_dir, args.artifacts_dir)
    capabilities = _selected_capabilities(repo_root, args.max_capabilities, args.max_features_per_capability)
    features: List[Dict[str, Any]] = []
    for capability in capabilities:
        for feature in capability["features"]:
            features.append(
                {
                    "capability_id": capability["id"],
                    "feature_id": feature["id"],
                    "feature_key": feature["key"],
                    "title": feature["title"],
                    "summary": feature["summary"],
                    "acceptance_boundary": "独立可验收的业务能力单元",
                    "acceptance_checks": feature["acceptance_checks"],
                    "preconditions": feature["preconditions"],
                    "main_flow": feature["main_flow"],
                    "edge_cases": feature["edge_cases"],
                    "state_updates": feature["state_updates"],
                    "code_refs": feature["code_refs"],
                    "primary_refs": feature["code_refs"],
                    "evidence_refs": feature.get("all_refs", feature["code_refs"]),
                    "evidence_layers": feature.get("evidence_layers", _build_evidence_layers(feature.get("all_refs", feature["code_refs"]))),
                    "evidence_strategy": dict(EVIDENCE_STRATEGY),
                }
            )
    payload = {"generated_at": _utc_now(), "features": features}
    try:
        registry_schema = _load_local_schema(repo_root, "spec-global/core/contracts/reverse-feature-registry/v2/schema.json")
        validate(instance=payload, schema=registry_schema)
    except ValidationError as exc:
        raise SystemExit(f"reverse-feature-registry v2 validation failed: {exc.message}")
    md_lines = ["# Feature Registry", "", f"- Generated At: `{payload['generated_at']}`", ""]
    for feature in payload["features"]:
        md_lines.extend([f"## {feature['feature_id']} {feature['title']}", f"- Capability: `{feature['capability_id']}`", f"- Key: `{feature['feature_key']}`", f"- Summary: {feature['summary']}", f"- Acceptance Boundary: {feature['acceptance_boundary']}", "- Preconditions:"])
        for item in feature["preconditions"]:
            md_lines.append(f"  - {item}")
        md_lines.append("- Main Flow:")
        for item in feature["main_flow"]:
            md_lines.append(f"  - {item}")
        md_lines.append("- Edge Cases:")
        for item in feature["edge_cases"]:
            md_lines.append(f"  - {item}")
        md_lines.append("- State Updates:")
        for item in feature["state_updates"]:
            md_lines.append(f"  - {item}")
        md_lines.append("- Acceptance Checks:")
        for check in feature["acceptance_checks"]:
            md_lines.append(f"  - `{check['id']}` {check['scenario']}")
            md_lines.append(f"    - Given: {check['given']}")
            md_lines.append(f"    - When: {check['when']}")
            md_lines.append(f"    - Then: {check['then']}")
            md_lines.append(f"    - Trace Hints: {', '.join(check['trace_hints'])}")
        md_lines.append("- Primary Refs:")
        for ref in feature["primary_refs"]:
            md_lines.append(f"  - `{ref}`")
        md_lines.extend(["- Evidence Layers:", "  - Impl Refs:"])
        for ref in feature["evidence_layers"]["impl_refs"]:
            md_lines.append(f"    - `{ref}`")
        md_lines.append("  - API Refs:")
        for ref in feature["evidence_layers"]["api_refs"]:
            md_lines.append(f"    - `{ref}`")
        md_lines.append("  - Test Refs:")
        for ref in feature["evidence_layers"]["test_refs"]:
            md_lines.append(f"    - `{ref}`")
        md_lines.append("  - Doc Refs:")
        for ref in feature["evidence_layers"]["doc_refs"]:
            md_lines.append(f"    - `{ref}`")
        md_lines.append("- Evidence Refs:")
        for ref in feature["evidence_refs"]:
            md_lines.append(f"  - `{ref}`")
        md_lines.append("")
    _write_text(paths["requirements_root"] / "feature-registry.md", "\n".join(md_lines))
    _write_json(paths["reports_root"] / "feature-registry.json", payload)
    print(json.dumps({"feature_count": len(features)}, ensure_ascii=False))
    return 0


def _epic_key(capability: Dict[str, Any]) -> str:
    return f"epic_{capability['id'].lower().replace('-', '_')}"


def _render_epic_markdown(epic_id: str, capability: Dict[str, Any], feature_ids: List[str]) -> str:
    lines = [f"# {epic_id} {capability['name']}", "", "## Summary", capability["summary"], "", "## Scope", capability["boundary"], "", "## Child Features"]
    for feature_id in feature_ids:
        lines.append(f"- `{feature_id}`")
    lines.extend(["", "## Code Refs"])
    for ref in capability["code_refs"]:
        lines.append(f"- `{ref}`")
    return "\n".join(lines)


def _render_feat_markdown(feat_id: str, epic_id: str, capability: Dict[str, Any], feature: Dict[str, Any]) -> str:
    lines = [f"# {feat_id} {feature['title']}", "", "## Summary", feature["summary"], "", "## Goal", feature["goal"], "", "## User Value", feature["user_value"], "", "## Parent EPIC", f"- `{epic_id}`", "", "## Capability Linkage", f"- `{capability['id']} {capability['name']}`", "", "## Scope"]
    for item in feature["scope"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Preconditions"])
    for item in feature["preconditions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Main Flow"])
    for item in feature["main_flow"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Processing"])
    for item in feature["processing"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Inputs"])
    for item in feature["inputs"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Outputs"])
    for item in feature["outputs"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Business Rules"])
    for item in feature["business_rules"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Dependencies"])
    for item in feature["dependencies"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Non-goals"])
    for item in feature["non_goals"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Edge Cases"])
    for item in feature["edge_cases"]:
        lines.append(f"- {item}")
    lines.extend(["", "## State Updates"])
    for item in feature["state_updates"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Acceptance Criteria"])
    for index, item in enumerate(feature["acceptance_criteria"], start=1):
        lines.append(f"- AC-{index:03d} {item}")
    lines.extend(["", "## Acceptance Checks"])
    for check in feature["acceptance_checks"]:
        lines.append(f"### {check['id']} {check['scenario']}")
        lines.append(f"- Given: {check['given']}")
        lines.append(f"- When: {check['when']}")
        lines.append(f"- Then: {check['then']}")
        lines.append(f"- Trace Hints: {', '.join(check['trace_hints'])}")
    lines.extend(["", "## Delivery Metadata", f"- Priority: `{feature['priority']}`", f"- Delivery Slice: `{feature['delivery_slice']}`", f"- Lifecycle Status: `{feature['lifecycle_status']}`"])
    lines.extend(["", "## Derived Object Expectations"])
    for key, value in feature["derived_object_expectations"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Code Refs"])
    for ref in feature["code_refs"]:
        lines.append(f"- `{ref}`")
    layers = feature.get("evidence_layers", {})
    lines.extend(["", "## Evidence Layers", "### Impl Refs"])
    for ref in layers.get("impl_refs", []):
        lines.append(f"- `{ref}`")
    lines.append("### API Refs")
    for ref in layers.get("api_refs", []):
        lines.append(f"- `{ref}`")
    lines.append("### Test Refs")
    for ref in layers.get("test_refs", []):
        lines.append(f"- `{ref}`")
    lines.append("### Doc Refs")
    for ref in layers.get("doc_refs", []):
        lines.append(f"- `{ref}`")
    lines.extend(["", "## Evidence Refs"])
    for ref in feature.get("all_refs", feature["code_refs"]):
        lines.append(f"- `{ref}`")
    lines.extend(["", "## Source Refs"])
    for ref in feature.get("all_refs", feature["code_refs"]):
        lines.append(f"- `{ref}`")
    lines.extend(["", "## Inference", "- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。"])
    return "\n".join(lines)


def run_materialize(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    paths = _project_paths(repo_root, args.specs_dir, args.docs_dir, args.artifacts_dir)
    strict_evidence = str(args.strict_evidence).lower() in {"1", "true", "yes"}
    capabilities = _selected_capabilities(repo_root, args.max_capabilities, args.max_features_per_capability)
    outputs: List[Dict[str, Any]] = []
    written_files: List[str] = []
    features_dir = paths["requirements_root"]
    features_dir.mkdir(parents=True, exist_ok=True)
    epic_registry: List[Dict[str, str]] = []
    feat_counter = 1
    for epic_counter, capability in enumerate(capabilities, start=1):
        epic_id = f"EPIC-{epic_counter:03d}"
        epic_key = _epic_key(capability)
        feature_ids = [feature["id"] for feature in capability["features"]]
        epic_content = _render_epic_markdown(epic_id, capability, feature_ids)
        epic_path = features_dir / f"{epic_id}.md"
        _write_text(epic_path, epic_content)
        written_files.append(_repo_relative(repo_root, epic_path))
        epic_layers = _build_evidence_layers(capability["code_refs"])
        outputs.append(
            {
                "key": epic_key,
                "identity_kind": "ssot",
                "ssot_type": "epic",
                "title": capability["name"],
                "description": capability["summary"],
                "content": epic_content,
                "source_refs": capability["code_refs"],
                "primary_refs": _primary_refs_from_layers(epic_layers),
                "evidence_layers": epic_layers,
                "evidence_strategy": dict(EVIDENCE_STRATEGY),
                "tags": ["reverse-ssot", "epic"],
            }
        )
        epic_registry.append({"epic_id": epic_id, "epic_key": epic_key, "title": capability["name"]})
        for feature in capability["features"]:
            if strict_evidence and not feature["code_refs"]:
                continue
            feat_id = f"FEAT-{feat_counter:03d}"
            feat_counter += 1
            feat_content = _render_feat_markdown(feat_id, epic_id, capability, feature)
            feat_path = features_dir / f"{feat_id}.md"
            _write_text(feat_path, feat_content)
            written_files.append(_repo_relative(repo_root, feat_path))
            outputs.append(
                {
                    "key": feature["key"],
                    "identity_kind": "ssot",
                    "ssot_type": "feat",
                    "title": feature["title"],
                    "description": feature["summary"],
                    "content": feat_content,
                    "parent": epic_key,
                    "derived_from": [capability["id"]],
                    "source_refs": feature.get("all_refs", feature["code_refs"]),
                    "primary_refs": feature["code_refs"],
                    "evidence_layers": feature.get("evidence_layers", _build_evidence_layers(feature.get("all_refs", feature["code_refs"]))),
                    "evidence_strategy": dict(EVIDENCE_STRATEGY),
                    "tags": ["reverse-ssot", "feat"],
                }
            )
    bundle = {"contract_version": "1.0", "workflow_id": "core.reverse-epic-feat", "run_id": args.run_id or f"reverse-epic-feat-{datetime.now().strftime('%Y%m%d%H%M%S')}", "outputs": outputs}
    _write_json(paths["artifacts_active_root"] / "reverse-epic-feat-ssot-output.json", bundle)
    registry_lines = ["# EPIC Registry", ""]
    for item in epic_registry:
        registry_lines.append(f"- `{item['epic_id']}` `{item['epic_key']}` {item['title']}")
    _write_text(features_dir / "epic-registry.md", "\n".join(registry_lines))
    print(json.dumps({"epic_count": len([item for item in outputs if item["ssot_type"] == "epic"]), "feat_count": len([item for item in outputs if item["ssot_type"] == "feat"]), "written_files": written_files}, ensure_ascii=False))
    return 0


def run_review(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    paths = _project_paths(repo_root, args.specs_dir, args.docs_dir, args.artifacts_dir)
    bundle = json.loads((paths["artifacts_active_root"] / "reverse-epic-feat-ssot-output.json").read_text(encoding="utf-8"))
    blockers: List[Dict[str, Any]] = []
    majors: List[Dict[str, Any]] = []
    try:
        ssot_agent_output_schema = _load_local_schema(repo_root, "spec-global/core/contracts/ssot-agent-output/v1/schema.json")
        validate(instance=bundle, schema=ssot_agent_output_schema)
    except ValidationError as exc:
        blockers.append({"rule": "ssot_agent_output_schema", "message": f"Bundle failed ssot-agent-output validation: {exc.message}"})
    outputs = bundle.get("outputs", [])
    epic_keys = {item["key"] for item in outputs if item.get("ssot_type") == "epic"}
    type_counter = Counter(item.get("ssot_type") for item in outputs)
    for item in outputs:
        ssot_type = item.get("ssot_type")
        if ssot_type not in {"epic", "feat"}:
            blockers.append({"rule": "ssot_type_scope", "message": f"Unsupported ssot_type: {ssot_type}"})
        if item.get("identity_kind") != "ssot":
            blockers.append({"rule": "identity_kind", "message": f"Output {item.get('key')} is not ssot"})
        if not item.get("source_refs"):
            blockers.append({"rule": "source_refs", "message": f"Output {item.get('key')} lacks source_refs"})
        for ref in item.get("source_refs", []):
            if not (repo_root / ref).exists():
                blockers.append({"rule": "code_ref_exists", "message": f"Missing source ref: {ref}"})
        evidence_layers = item.get("evidence_layers") or {}
        if not isinstance(evidence_layers, dict):
            blockers.append({"rule": "evidence_layers", "message": f"Output {item.get('key')} has invalid evidence_layers"})
            evidence_layers = {}
        else:
            missing_layer_keys = [key for key in ("impl_refs", "api_refs", "test_refs", "doc_refs") if key not in evidence_layers]
            if missing_layer_keys:
                blockers.append({"rule": "evidence_layers_shape", "message": f"Output {item.get('key')} missing layer keys: {', '.join(missing_layer_keys)}"})
        primary_refs = item.get("primary_refs") or []
        evidence_strategy = item.get("evidence_strategy") or {}
        if not evidence_strategy:
            blockers.append({"rule": "evidence_strategy", "message": f"Output {item.get('key')} lacks evidence_strategy"})
        else:
            if evidence_strategy.get("primary_selection") != EVIDENCE_STRATEGY["primary_selection"]:
                majors.append({"rule": "evidence_strategy_primary_selection", "message": f"Output {item.get('key')} has unexpected primary_selection"})
            ranking_signals = evidence_strategy.get("ranking_signals") or []
            if ranking_signals != EVIDENCE_STRATEGY["ranking_signals"]:
                majors.append({"rule": "evidence_strategy_ranking_signals", "message": f"Output {item.get('key')} has unexpected ranking_signals ordering or values"})
        if ssot_type == "feat":
            if not primary_refs:
                blockers.append({"rule": "primary_refs", "message": f"FEAT {item.get('key')} lacks primary_refs"})
            if not item.get("content"):
                blockers.append({"rule": "feat_content", "message": f"FEAT {item.get('key')} lacks content"})
            else:
                content = item["content"]
                required_sections = (
                    "Goal",
                    "User Value",
                    "Preconditions",
                    "Main Flow",
                    "Processing",
                    "Business Rules",
                    "Dependencies",
                    "Non-goals",
                    "Edge Cases",
                    "State Updates",
                    "Acceptance Criteria",
                    "Acceptance Checks",
                    "Delivery Metadata",
                    "Derived Object Expectations",
                )
                missing_sections = [section for section in required_sections if not _has_markdown_section(content, section)]
                if missing_sections:
                    blockers.append({"rule": "feat_required_sections", "message": f"FEAT {item.get('key')} missing sections: {', '.join(missing_sections)}"})
                if _count_section_bullets(content, "Acceptance Criteria") < 2:
                    majors.append({"rule": "feat_acceptance_depth", "message": f"FEAT {item.get('key')} has fewer than 2 acceptance criteria"})
                if _count_acceptance_check_blocks(content) < 2:
                    blockers.append({"rule": "feat_acceptance_checks", "message": f"FEAT {item.get('key')} lacks at least 2 structured acceptance checks"})
                if _count_section_bullets(content, "Business Rules") < 2:
                    majors.append({"rule": "feat_business_rule_depth", "message": f"FEAT {item.get('key')} has fewer than 2 business rules"})
                if _count_section_bullets(content, "Main Flow") < 2:
                    majors.append({"rule": "feat_outline_only", "message": f"FEAT {item.get('key')} main flow is too brief and still reads like an outline"})
                if _count_section_bullets(content, "Dependencies") < 1:
                    majors.append({"rule": "feat_dependency_depth", "message": f"FEAT {item.get('key')} lacks explicit dependencies"})
            for ref in primary_refs:
                ref_class = _classify_ref(ref)
                if evidence_layers.get("impl_refs") or evidence_layers.get("api_refs"):
                    if ref_class not in {"impl", "api"}:
                        majors.append({"rule": "primary_ref_noise", "message": f"FEAT {item.get('key')} primary ref {ref} should not be doc/test when impl/api refs exist"})
            for layer_key in ("impl_refs", "api_refs", "test_refs", "doc_refs"):
                for ref in evidence_layers.get(layer_key, []):
                    if ref not in item.get("source_refs", []):
                        majors.append({"rule": "evidence_layer_membership", "message": f"FEAT {item.get('key')} layer ref {ref} is missing from source_refs"})
        if ssot_type == "feat":
            if not item.get("parent"):
                blockers.append({"rule": "feat_parent", "message": f"FEAT {item.get('key')} lacks parent"})
            elif item["parent"] not in epic_keys:
                blockers.append({"rule": "feat_parent", "message": f"FEAT {item.get('key')} parent is not an EPIC key"})
            if args.strict_evidence and not item.get("source_refs"):
                blockers.append({"rule": "strict_evidence", "message": f"FEAT {item.get('key')} lacks code refs"})
        if ssot_type == "epic":
            if item.get("parent"):
                blockers.append({"rule": "epic_parent", "message": f"EPIC {item.get('key')} should not have a parent"})
    if not outputs:
        blockers.append({"rule": "empty_bundle", "message": "No EPIC/FEAT outputs were generated"})
    if type_counter.get("epic", 0) == 0:
        blockers.append({"rule": "missing_epic", "message": "No EPIC outputs generated"})
    if type_counter.get("feat", 0) == 0:
        blockers.append({"rule": "missing_feat", "message": "No FEAT outputs generated"})
    report = {
        "generated_at": _utc_now(),
        "summary": {"epic_count": type_counter.get("epic", 0), "feat_count": type_counter.get("feat", 0), "blocker_count": len(blockers), "major_count": len(majors)},
        "findings": {"blockers": blockers, "majors": majors},
        "rules_checked": [
            "Only epic/feat ssot_type outputs are allowed",
            "Bundle must satisfy ssot-agent-output contract",
            "Every FEAT must have a valid EPIC parent",
            "Every output must carry existing source_refs",
            "FEAT outputs must carry structured evidence_layers, primary_refs, and evidence_strategy",
            "Every FEAT must include goal, user value, preconditions, main flow, processing, dependencies, non-goals, edge cases, state updates, testable acceptance criteria, and structured acceptance checks",
            "Primary refs must prefer impl/api evidence when available",
            "Template/runtime boundary stays outside checked-in spec files",
        ],
    }
    _write_json(paths["reports_root"] / "reverse-epic-feat-review.json", report)
    print(json.dumps({"blocker_count": len(blockers), "major_count": len(majors)}, ensure_ascii=False))
    return 0


def run_complete(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    paths = _project_paths(repo_root, args.specs_dir, args.docs_dir, args.artifacts_dir)
    review = json.loads((paths["reports_root"] / "reverse-epic-feat-review.json").read_text(encoding="utf-8"))
    bundle_path = paths["artifacts_active_root"] / "reverse-epic-feat-ssot-output.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    blockers = int(review["summary"].get("blocker_count", 0))
    majors = int(review["summary"].get("major_count", 0))
    epic_count = int(review["summary"].get("epic_count", 0))
    feat_count = int(review["summary"].get("feat_count", 0))
    publish_mode = args.publish_mode
    if blockers > 0:
        status = "blocked"
    elif publish_mode == "freeze":
        status = "frozen" if majors == 0 else "review_warning"
    elif publish_mode == "publish":
        status = "published"
    else:
        status = "draft_generated" if majors == 0 else "review_warning"
    lines = [
        "# Reverse EPIC/FEAT Completion",
        "",
        f"- Generated At: `{_utc_now()}`",
        f"- Publish Mode: `{publish_mode}`",
        f"- Final Status: `{status}`",
        f"- Blockers: `{blockers}`",
        f"- Majors: `{majors}`",
        "",
        "## Output Bundle",
        f"- `{_repo_relative(repo_root, paths['artifacts_active_root'] / 'reverse-epic-feat-ssot-output.json')}`",
        "",
        "## Review Report",
        f"- `{_repo_relative(repo_root, paths['reports_root'] / 'reverse-epic-feat-review.json')}`",
    ]
    completion_summary_path = paths["reports_root"] / "reverse-epic-feat-completion.md"
    _write_text(completion_summary_path, "\n".join(lines))
    output_payload = {
        "request_id": args.request_id or bundle.get("run_id", ""),
        "workflow_id": bundle.get("workflow_id", "core.reverse-epic-feat"),
        "run_id": bundle.get("run_id", ""),
        "system_map_path": _repo_relative(repo_root, paths["guides_root"] / "system-map.md"),
        "capability_map_path": _repo_relative(repo_root, paths["guides_root"] / "capability-map.md"),
        "feature_registry_path": _repo_relative(repo_root, paths["requirements_root"] / "feature-registry.md"),
        "epic_feat_ssot_output_path": _repo_relative(repo_root, bundle_path),
        "review_report_path": _repo_relative(repo_root, paths["reports_root"] / "reverse-epic-feat-review.json"),
        "completion_summary_path": _repo_relative(repo_root, completion_summary_path),
        "epic_count": epic_count,
        "feat_count": feat_count,
        "blocker_count": blockers,
        "major_count": majors,
        "evidence_strategy_version": "1.0",
        "evidence_layering_enabled": True,
        "primary_ref_ranking_signals": list(EVIDENCE_STRATEGY["ranking_signals"]),
        "reverse_ssot_status": status,
    }
    _write_json(paths["reports_root"] / "reverse-epic-feat-output.json", output_payload)
    print(json.dumps(output_payload, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reverse EPIC/FEAT deterministic workflow helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--repo-root", required=True)
        sub.add_argument("--specs-dir", default="spec")
        sub.add_argument("--docs-dir", default="docs")
        sub.add_argument("--artifacts-dir", default=".artifacts")
        sub.add_argument("--request-id", default="")

    scan = subparsers.add_parser("scan")
    add_common(scan)
    scan.add_argument("--include-paths", default="")
    scan.add_argument("--exclude-paths", default="")
    scan.set_defaults(func=run_scan)

    system_map = subparsers.add_parser("system-map")
    add_common(system_map)
    system_map.set_defaults(func=run_system_map)

    capability_map = subparsers.add_parser("capability-map")
    add_common(capability_map)
    capability_map.add_argument("--max-capabilities", type=int, default=12)
    capability_map.add_argument("--max-features-per-capability", type=int, default=8)
    capability_map.set_defaults(func=run_capability_map)

    feature_registry = subparsers.add_parser("feature-registry")
    add_common(feature_registry)
    feature_registry.add_argument("--max-capabilities", type=int, default=12)
    feature_registry.add_argument("--max-features-per-capability", type=int, default=8)
    feature_registry.set_defaults(func=run_feature_registry)

    materialize = subparsers.add_parser("materialize")
    add_common(materialize)
    materialize.add_argument("--max-capabilities", type=int, default=12)
    materialize.add_argument("--max-features-per-capability", type=int, default=8)
    materialize.add_argument("--strict-evidence", default="true")
    materialize.add_argument("--run-id", default="")
    materialize.set_defaults(func=run_materialize)

    review = subparsers.add_parser("review")
    add_common(review)
    review.add_argument("--strict-evidence", action="store_true")
    review.set_defaults(func=run_review)

    complete = subparsers.add_parser("complete")
    add_common(complete)
    complete.add_argument("--publish-mode", default="draft")
    complete.set_defaults(func=run_complete)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
