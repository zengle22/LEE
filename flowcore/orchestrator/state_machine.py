"""
State Machine - 工作流状态机实现

核心功能：
1. 维护当前执行状态
2. 检查步骤依赖
3. 强制门禁通过
4. 阻止非法状态转换
"""

import yaml
import json
import hashlib
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict


class StepState(Enum):
    """步骤状态"""
    PENDING = "pending"           # 等待执行
    BLOCKED = "blocked"           # 被依赖阻断
    READY = "ready"               # 可以执行
    IN_PROGRESS = "in_progress"   # 执行中
    VALIDATING = "validating"     # 验证中
    GATE_PENDING = "gate_pending" # 等待门禁
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    SKIPPED = "skipped"           # 跳过
    # 新增: 测试流程扩展状态
    WAITING_EXTERNAL = "waiting_external"  # 等待外部事件 (如: 等待开发修复)
    LOOP_ITERATION = "loop_iteration"      # 循环迭代中


class RunState(Enum):
    """运行状态"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"         # 等待门禁
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    # 新增: 测试流程扩展状态
    WAITING_EXTERNAL = "waiting_external"  # 等待外部事件
    LOOPING = "looping"                    # 循环执行中


@dataclass
class StepStatus:
    """步骤状态详情"""
    step_id: str
    state: StepState
    agent_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    token: Optional[str] = None
    inputs_hash: Optional[str] = None
    outputs: List[str] = field(default_factory=list)
    outputs_hash: Optional[str] = None
    validation_result: Optional[Dict] = None
    gate_id: Optional[str] = None
    gate_status: Optional[str] = None
    error: Optional[str] = None
    # 新增: 循环和外部等待支持
    loop_iteration: Optional[int] = None       # 当前循环次数
    loop_max: Optional[int] = None             # 最大循环次数
    waiting_for_event: Optional[str] = None    # 等待的外部事件类型
    wait_timeout: Optional[str] = None         # 等待超时时间


@dataclass
class GateStatus:
    """门禁状态"""
    gate_id: str
    step_id: str
    type: str  # human / auto
    status: str  # pending / approved / rejected
    blocking: bool = True
    triggered_at: Optional[str] = None
    approved_at: Optional[str] = None
    approver: Optional[str] = None
    approval_artifact: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class LoopContext:
    """循环上下文 - 用于测试流程等需要迭代的场景"""
    loop_id: str                      # 循环标识 (通常是 stage/step ID)
    condition: str                     # 循环条件表达式
    max_iterations: int                # 最大迭代次数
    current_iteration: int = 0         # 当前迭代
    body_steps: List[str] = field(default_factory=list)  # 循环体步骤
    started_at: Optional[str] = None
    last_iteration_at: Optional[str] = None
    status: str = "pending"            # pending / running / completed / max_reached / failed


@dataclass
class ExternalWait:
    """外部事件等待 - 用于等待开发修复等外部事件"""
    wait_id: str
    step_id: str
    event_type: str                    # 等待的事件类型
    timeout: str                       # 超时时间 (如: "48h")
    timeout_action: str = "escalate"   # timeout 时的动作
    notify_channels: List[str] = field(default_factory=list)
    triggered_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    event_data: Optional[Dict] = None  # 事件携带的数据
    status: str = "waiting"            # waiting / resolved / timeout


class StateMachine:
    """工作流状态机"""

    STATE_FILE = ".workflow/state.yaml"
    ARTIFACTS_DIR = ".workflow/artifacts"
    APPROVALS_DIR = ".workflow/approvals"

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.state_path = self.project_dir / self.STATE_FILE
        self.artifacts_dir = self.project_dir / self.ARTIFACTS_DIR
        self.approvals_dir = self.project_dir / self.APPROVALS_DIR
        self._state: Optional[Dict] = None
        self._workflow: Optional[Dict] = None

    def init(self, workflow: Dict, run_id: str = None) -> str:
        """初始化工作流运行"""
        # 创建目录
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.approvals_dir.mkdir(parents=True, exist_ok=True)

        if run_id is None:
            run_id = f"RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # 解析 workflow 获取所有步骤
        steps = self._extract_steps(workflow)

        # 创建步骤状态 (手动转为 dict 避免 enum 序列化问题)
        steps_dict = {}
        deps_dict = {}  # 保存依赖关系
        gates_dict = {}  # 保存门禁信息

        for s in steps:
            step_id = s["id"]
            steps_dict[step_id] = {
                "step_id": step_id,
                "state": StepState.PENDING.value,
                "agent_id": None,
                "started_at": None,
                "completed_at": None,
                "token": None,
                "inputs_hash": None,
                "outputs": [],
                "outputs_hash": None,
                "validation_result": None,
                "gate_id": s.get("gate"),
                "gate_status": None,
                "error": None,
                "mandatory": s.get("mandatory", False),
                "required_outputs": s.get("required_outputs", s.get("outputs", []))  # 新增: 必需输出
            }
            # 保存依赖关系
            deps_dict[step_id] = s.get("deps", [])

        # 提取循环定义
        loops_dict = self._extract_loops(workflow)

        self._state = {
            "version": "1.1",  # 升级版本以支持新特性
            "run_id": run_id,
            "workflow_id": workflow.get("id", "unknown"),
            "workflow_name": workflow.get("name", "unknown"),
            "run_state": RunState.CREATED.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "current_step": None,
            "steps": steps_dict,
            "_deps": deps_dict,  # 内部依赖映射
            "gates": {},
            "artifacts": {},
            "metadata": {},
            # 新增: 测试流程扩展
            "loops": loops_dict,           # 循环定义
            "external_waits": {},          # 外部事件等待
            "loop_back_targets": {}        # loop_back 目标映射
        }

        self._workflow = workflow
        self._save_state()
        return run_id

    def _extract_steps(self, workflow: Dict) -> List[Dict]:
        """从 workflow 中提取所有步骤

        支持两种格式:
        1. 嵌套格式: stages -> steps
        2. 扁平格式: steps 直接在顶层
        """
        steps = []

        # 格式1: 嵌套 stages -> steps
        if "stages" in workflow:
            for stage in workflow.get("stages", []):
                for step in stage.get("steps", []):
                    steps.append({
                        "id": step.get("id"),
                        "name": step.get("name"),
                        "agent_id": step.get("run"),
                        "deps": step.get("dependencies", {}).get("requires", []),
                        "outputs": step.get("outputs", []),
                        "gate": step.get("human_gate"),
                        "validators": step.get("output_validation")
                    })

        # 格式2: 扁平 steps (phase-openspec-flow 格式)
        elif "steps" in workflow:
            for step in workflow.get("steps", []):
                # 获取 agent/skill 引用
                run_ref = step.get("run", "")
                if isinstance(run_ref, dict):
                    run_ref = run_ref.get("fallback", "unknown")

                # 提取输出路径 (保留完整定义用于验证)
                outputs = []
                required_outputs = []  # 新增: 必需输出列表
                for out in step.get("outputs", []):
                    if isinstance(out, dict):
                        path = out.get("path", "")
                        outputs.append(path)
                        # 默认 required=True，除非显式设置为 false
                        if out.get("required", True):
                            required_outputs.append(path)
                    elif isinstance(out, str):
                        outputs.append(out)
                        required_outputs.append(out)  # 字符串格式默认必需

                steps.append({
                    "id": step.get("id"),
                    "name": step.get("name"),
                    "agent_id": run_ref,
                    "deps": step.get("depends_on", []),
                    "outputs": outputs,
                    "required_outputs": required_outputs,  # 新增: 必需输出
                    "gate": step.get("human_gate"),
                    "validators": step.get("output_validation"),
                    "mandatory": step.get("mandatory", False)
                })

        return steps

    def _extract_loops(self, workflow: Dict) -> Dict:
        """从 workflow 中提取循环定义

        循环在测试流程中用于 bug 修复验证循环等场景。

        示例 workflow 格式:
        stages:
          - id: t5_bug_fix_cycle
            loop:
              condition: "open_bugs.count > 0"
              max_cycles: 5
            steps: [...]
        """
        loops = {}

        for stage in workflow.get("stages", []):
            loop_def = stage.get("loop")
            if loop_def:
                loop_id = stage.get("id")
                body_steps = [s.get("id") for s in stage.get("steps", [])]

                loops[loop_id] = {
                    "loop_id": loop_id,
                    "condition": loop_def.get("condition", "true"),
                    "max_iterations": loop_def.get("max_cycles", loop_def.get("max_iterations", 10)),
                    "current_iteration": 0,
                    "body_steps": body_steps,
                    "started_at": None,
                    "last_iteration_at": None,
                    "status": "pending"
                }

        return loops

    def load(self) -> Dict:
        """加载状态"""
        if self._state is None:
            if not self.state_path.exists():
                raise FileNotFoundError(f"State file not found: {self.state_path}")
            with open(self.state_path, encoding='utf-8') as f:
                self._state = yaml.safe_load(f)
        return self._state

    def _save_state(self):
        """保存状态"""
        self._state["updated_at"] = datetime.now().isoformat()
        with open(self.state_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._state, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def get_run_state(self) -> RunState:
        """获取运行状态"""
        state = self.load()
        return RunState(state["run_state"])

    def get_step_state(self, step_id: str) -> StepStatus:
        """获取步骤状态"""
        state = self.load()
        step_data = state["steps"].get(step_id)
        if not step_data:
            raise ValueError(f"Step not found: {step_id}")
        return StepStatus(
            step_id=step_data["step_id"],
            state=StepState(step_data["state"]),
            agent_id=step_data.get("agent_id"),
            started_at=step_data.get("started_at"),
            completed_at=step_data.get("completed_at"),
            token=step_data.get("token"),
            outputs=step_data.get("outputs", []),
            validation_result=step_data.get("validation_result"),
            gate_id=step_data.get("gate_id"),
            gate_status=step_data.get("gate_status"),
            error=step_data.get("error")
        )

    def can_start_step(self, step_id: str) -> Tuple[bool, Optional[str]]:
        """检查是否可以开始步骤"""
        state = self.load()

        # 检查步骤是否存在
        if step_id not in state["steps"]:
            return False, f"Step not found: {step_id}"

        step = state["steps"][step_id]

        # 检查当前状态
        if step["state"] not in [StepState.PENDING.value, StepState.READY.value]:
            return False, f"Step {step_id} is not in pending/ready state (current: {step['state']})"

        # 检查是否有阻断性门禁未通过
        for gate_id, gate in state.get("gates", {}).items():
            if gate["blocking"] and gate["status"] == "pending":
                return False, f"Blocked by pending gate: {gate_id}"

        # 检查依赖是否完成 - 从 workflow 元数据获取依赖关系
        deps = state.get("_deps", {}).get(step_id, [])
        for dep_id in deps:
            if dep_id in state["steps"]:
                dep_state = state["steps"][dep_id]["state"]
                if dep_state != StepState.COMPLETED.value:
                    return False, f"Dependency {dep_id} not completed (current: {dep_state})"

        return True, None

    def start_step(self, step_id: str, agent_id: str = None, token: str = None) -> Tuple[bool, Optional[str]]:
        """开始执行步骤"""
        can_start, reason = self.can_start_step(step_id)
        if not can_start:
            return False, reason

        state = self.load()
        state["steps"][step_id].update({
            "state": StepState.IN_PROGRESS.value,
            "agent_id": agent_id,
            "started_at": datetime.now().isoformat(),
            "token": token
        })
        state["current_step"] = step_id
        state["run_state"] = RunState.RUNNING.value

        self._save_state()
        return True, None

    def complete_step(self, step_id: str, outputs: List[str] = None) -> Tuple[bool, Optional[str]]:
        """完成步骤 (进入验证阶段)"""
        state = self.load()

        if step_id not in state["steps"]:
            return False, f"Step not found: {step_id}"

        step = state["steps"][step_id]
        if step["state"] != StepState.IN_PROGRESS.value:
            return False, f"Step {step_id} is not in progress"

        # 计算输出 hash
        outputs_hash = None
        if outputs:
            outputs_hash = self._compute_outputs_hash(outputs)

        state["steps"][step_id].update({
            "state": StepState.VALIDATING.value,
            "outputs": outputs or [],
            "outputs_hash": outputs_hash
        })

        self._save_state()
        return True, None

    def _compute_outputs_hash(self, outputs: List[str]) -> str:
        """计算输出文件的 hash"""
        hasher = hashlib.sha256()
        for output in sorted(outputs):
            path = self.project_dir / output
            if path.exists():
                hasher.update(path.read_bytes())
        return hasher.hexdigest()[:16]

    def set_validation_result(self, step_id: str, passed: bool, details: Dict = None) -> Tuple[bool, Optional[str]]:
        """设置验证结果"""
        state = self.load()

        if step_id not in state["steps"]:
            return False, f"Step not found: {step_id}"

        step = state["steps"][step_id]
        if step["state"] != StepState.VALIDATING.value:
            return False, f"Step {step_id} is not in validating state"

        state["steps"][step_id]["validation_result"] = {
            "passed": passed,
            "validated_at": datetime.now().isoformat(),
            "details": details or {}
        }

        if passed:
            # 检查是否有门禁
            gate_id = step.get("gate_id")
            if gate_id:
                state["steps"][step_id]["state"] = StepState.GATE_PENDING.value
                # 自动触发门禁注册
                self._save_state()  # 先保存状态
                self.trigger_gate(gate_id, step_id, gate_type="human", blocking=True)
                return True, None
            else:
                state["steps"][step_id].update({
                    "state": StepState.COMPLETED.value,
                    "completed_at": datetime.now().isoformat()
                })
        else:
            state["steps"][step_id]["state"] = StepState.FAILED.value

        self._save_state()
        return True, None

    def trigger_gate(self, gate_id: str, step_id: str, gate_type: str = "human", blocking: bool = True) -> str:
        """触发门禁"""
        state = self.load()

        gate = GateStatus(
            gate_id=gate_id,
            step_id=step_id,
            type=gate_type,
            status="pending",
            blocking=blocking,
            triggered_at=datetime.now().isoformat()
        )

        state["gates"][gate_id] = asdict(gate)

        # 更新步骤状态
        if step_id in state["steps"]:
            state["steps"][step_id]["gate_id"] = gate_id
            state["steps"][step_id]["gate_status"] = "pending"

        if blocking:
            state["run_state"] = RunState.PAUSED.value

        self._save_state()
        return gate_id

    def approve_gate(self, gate_id: str, approver: str, comment: str = None) -> Tuple[bool, str]:
        """审批门禁，生成 approval artifact"""
        state = self.load()

        if gate_id not in state["gates"]:
            return False, f"Gate not found: {gate_id}"

        gate = state["gates"][gate_id]
        if gate["status"] != "pending":
            return False, f"Gate {gate_id} is not pending"

        # 生成 approval artifact
        approval = {
            "gate_id": gate_id,
            "step_id": gate["step_id"],
            "run_id": state["run_id"],
            "approver": approver,
            "approved_at": datetime.now().isoformat(),
            "comment": comment,
            "artifacts_hash": self._compute_step_artifacts_hash(gate["step_id"]),
            "signature": None  # 可以添加数字签名
        }

        # 计算 approval 的 hash 作为标识
        approval_hash = hashlib.sha256(
            json.dumps(approval, sort_keys=True).encode()
        ).hexdigest()[:16]

        approval["approval_id"] = f"APPR-{approval_hash}"

        # 保存 approval artifact
        approval_path = self.approvals_dir / f"{gate_id}.json"
        with open(approval_path, 'w', encoding='utf-8') as f:
            json.dump(approval, f, indent=2, ensure_ascii=False)

        # 更新门禁状态
        state["gates"][gate_id].update({
            "status": "approved",
            "approved_at": datetime.now().isoformat(),
            "approver": approver,
            "approval_artifact": str(approval_path.relative_to(self.project_dir)),
            "comment": comment
        })

        # 更新步骤状态
        step_id = gate["step_id"]
        if step_id in state["steps"]:
            state["steps"][step_id].update({
                "gate_status": "approved",
                "state": StepState.COMPLETED.value,
                "completed_at": datetime.now().isoformat()
            })

        # 检查是否还有其他阻断门禁
        has_blocking_gate = any(
            g["blocking"] and g["status"] == "pending"
            for g in state["gates"].values()
        )
        if not has_blocking_gate:
            state["run_state"] = RunState.RUNNING.value

        self._save_state()
        return True, approval["approval_id"]

    def reject_gate(self, gate_id: str, approver: str, reason: str) -> Tuple[bool, Optional[str]]:
        """拒绝门禁"""
        state = self.load()

        if gate_id not in state["gates"]:
            return False, f"Gate not found: {gate_id}"

        state["gates"][gate_id].update({
            "status": "rejected",
            "approved_at": datetime.now().isoformat(),
            "approver": approver,
            "comment": reason
        })

        # 更新步骤状态
        step_id = state["gates"][gate_id]["step_id"]
        if step_id in state["steps"]:
            state["steps"][step_id].update({
                "gate_status": "rejected",
                "state": StepState.FAILED.value,
                "error": f"Gate rejected: {reason}"
            })

        state["run_state"] = RunState.FAILED.value

        self._save_state()
        return True, None

    def _compute_step_artifacts_hash(self, step_id: str) -> str:
        """计算步骤产物的 hash"""
        state = self.load()
        step = state["steps"].get(step_id, {})
        outputs = step.get("outputs", [])
        return self._compute_outputs_hash(outputs)

    def has_valid_approval(self, step_id: str) -> Tuple[bool, Optional[str]]:
        """检查步骤是否有有效的审批"""
        state = self.load()

        # 查找与步骤关联的门禁
        for gate_id, gate in state.get("gates", {}).items():
            if gate["step_id"] == step_id:
                if gate["status"] == "approved":
                    approval_path = self.project_dir / gate.get("approval_artifact", "")
                    if approval_path.exists():
                        return True, gate["approval_artifact"]
                    else:
                        return False, "Approval artifact not found"
                elif gate["status"] == "pending":
                    return False, f"Gate {gate_id} is pending approval"
                else:
                    return False, f"Gate {gate_id} was rejected"

        # 没有门禁要求
        return True, None

    def get_ready_steps(self) -> List[str]:
        """获取可以执行的步骤列表"""
        state = self.load()
        ready = []

        for step_id, step in state["steps"].items():
            if step["state"] in [StepState.PENDING.value, StepState.READY.value]:
                can_start, _ = self.can_start_step(step_id)
                if can_start:
                    ready.append(step_id)

        return ready

    def get_pending_gates(self) -> List[GateStatus]:
        """获取待审批的门禁"""
        state = self.load()
        pending = []

        for gate_id, gate in state.get("gates", {}).items():
            if gate["status"] == "pending":
                pending.append(GateStatus(**gate))

        return pending

    def reset_step(self, step_id: str, reason: str = None) -> Tuple[bool, Optional[str]]:
        """重置步骤状态为 pending，允许重试

        这是处理验证失败或需要重新执行的标准机制。
        """
        state = self.load()

        if step_id not in state["steps"]:
            return False, f"Step not found: {step_id}"

        step = state["steps"][step_id]

        # 只能重置失败或已完成的步骤
        if step["state"] not in [StepState.FAILED.value, StepState.COMPLETED.value, StepState.VALIDATING.value]:
            return False, f"Cannot reset step in {step['state']} state"

        # 保存重置前的状态用于审计
        previous_state = step["state"]

        # 重置步骤状态
        state["steps"][step_id].update({
            "state": StepState.PENDING.value,
            "started_at": None,
            "completed_at": None,
            "token": None,
            "outputs": [],
            "outputs_hash": None,
            "validation_result": None,
            "error": None
        })

        # 记录重置历史
        if "reset_history" not in state["steps"][step_id]:
            state["steps"][step_id]["reset_history"] = []

        state["steps"][step_id]["reset_history"].append({
            "previous_state": previous_state,
            "reset_at": datetime.now().isoformat(),
            "reason": reason
        })

        # 如果当前步骤是这个，清除
        if state.get("current_step") == step_id:
            state["current_step"] = None

        self._save_state()
        return True, None

    def get_next_step_info(self) -> Optional[Dict]:
        """获取下一步的门禁信息，用于 run-to-gate 决策

        返回:
            {
                "next_step": step_id | null,
                "next_step_human_gate": true | false,
                "action": "continue" | "wait_for_approval" | "workflow_done"
            }
        """
        state = self.load()

        # 检查是否有待审批门禁
        pending_gates = self.get_pending_gates()
        if pending_gates:
            return {
                "next_step": None,
                "next_step_human_gate": True,
                "action": "wait_for_approval",
                "gate_id": pending_gates[0].gate_id
            }

        # 获取就绪步骤
        ready_steps = self.get_ready_steps()
        if not ready_steps:
            # 检查是否全部完成
            all_completed = all(
                s["state"] == StepState.COMPLETED.value
                for s in state["steps"].values()
            )
            if all_completed:
                return {
                    "next_step": None,
                    "next_step_human_gate": False,
                    "action": "workflow_done"
                }
            return {
                "next_step": None,
                "next_step_human_gate": False,
                "action": "blocked"
            }

        # 获取下一步的门禁信息
        next_step_id = ready_steps[0]
        step_data = state["steps"][next_step_id]
        has_gate = bool(step_data.get("gate_id"))

        return {
            "next_step": next_step_id,
            "next_step_human_gate": has_gate,
            "action": "continue"
        }

    def _get_required_outputs_from_workflow(self, step_id: str) -> List[str]:
        """从 workflow.yaml 动态获取步骤的 required_outputs

        用于处理在 required_outputs 字段添加之前初始化的 workflow。
        """
        workflow_path = self.project_dir / "workflow.yaml"
        if not workflow_path.exists():
            return []

        try:
            with open(workflow_path, encoding='utf-8') as f:
                workflow = yaml.safe_load(f)

            for step in workflow.get("steps", []):
                if step.get("id") == step_id:
                    outputs = []
                    for out in step.get("outputs", []):
                        if isinstance(out, dict):
                            path = out.get("path", "")
                            # 默认 required=True，除非显式设置为 false
                            if out.get("required", True):
                                outputs.append(path)
                        elif isinstance(out, str):
                            outputs.append(out)
                    return outputs
        except Exception:
            pass

        return []

    def verify_required_outputs(self, step_id: str, provided_outputs: List[str] = None) -> Dict:
        """验证步骤的必需输出是否全部存在

        这是交付物强约束的核心方法：
        - 从 workflow 定义获取 required_outputs
        - 检查文件是否实际存在
        - 返回验证结果和缺失清单

        Returns:
            {
                "passed": bool,
                "required": [...],      # workflow 定义的必需输出
                "provided": [...],      # agent 声明的输出
                "missing": [...],       # 缺失的文件
                "extra": [...],         # 额外提供的文件
                "manifest": {...}       # 用于记录的 manifest
            }
        """
        state = self.load()

        if step_id not in state["steps"]:
            return {"passed": False, "error": f"Step not found: {step_id}"}

        step = state["steps"][step_id]
        required = step.get("required_outputs", [])

        # 如果 state 中没有 required_outputs，从 workflow.yaml 动态读取
        if not required:
            required = self._get_required_outputs_from_workflow(step_id)

        provided = provided_outputs or step.get("outputs", [])

        # 加载项目配置用于路径解析
        from .project_config import ProjectConfig
        try:
            project_config = ProjectConfig.load(str(self.project_dir))
        except Exception:
            project_config = None

        # 检查必需文件是否存在
        missing = []
        found = []
        for req_item in required:
            # Handle both string and dict output formats
            if isinstance(req_item, dict):
                req_path = req_item.get("path", "")
            else:
                req_path = req_item

            if not isinstance(req_path, str) or not req_path:
                continue

            # 解析路径别名
            if project_config and (req_path.startswith("@") or req_path.startswith("${")):
                resolved = project_config.resolve_path(req_path, self.project_dir)
                path = Path(resolved)
            elif Path(req_path).is_absolute():
                path = Path(req_path)
            else:
                path = self.project_dir / req_path

            if path.exists():
                found.append(req_path)
            else:
                missing.append(req_path)

        # 检查额外提供的文件
        extra = [p for p in provided if p not in required]

        # 生成 manifest
        manifest = {
            "step": step_id,
            "verified_at": datetime.now().isoformat(),
            "required": required,
            "produced": found,
            "missing": missing,
            "extra": extra,
            "status": "done" if not missing else "incomplete"
        }

        return {
            "passed": len(missing) == 0,
            "required": required,
            "provided": provided,
            "found": found,
            "missing": missing,
            "extra": extra,
            "manifest": manifest
        }

    def write_step_manifest(self, step_id: str, manifest: Dict) -> str:
        """写入步骤的产物清单 (manifest)

        清单记录了步骤产出的所有文件，用于审计和追溯。
        """
        manifests_dir = self.project_dir / ".workflow" / "manifests"
        manifests_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = manifests_dir / f"{step_id}.manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return str(manifest_path.relative_to(self.project_dir))

    # ============================================
    # 测试流程扩展: 循环支持
    # ============================================

    def start_loop(self, loop_id: str) -> Tuple[bool, Optional[str]]:
        """开始循环执行

        测试流程中用于 bug 修复验证循环等场景。
        """
        state = self.load()

        if "loops" not in state:
            return False, "Loops not supported in this workflow version"

        if loop_id not in state.get("loops", {}):
            return False, f"Loop not found: {loop_id}"

        loop = state["loops"][loop_id]

        if loop["status"] == "running":
            return False, f"Loop {loop_id} is already running"

        if loop["current_iteration"] >= loop["max_iterations"]:
            return False, f"Loop {loop_id} has reached max iterations"

        loop["status"] = "running"
        loop["started_at"] = loop.get("started_at") or datetime.now().isoformat()
        loop["current_iteration"] += 1
        loop["last_iteration_at"] = datetime.now().isoformat()

        # 重置循环体内的所有步骤
        for step_id in loop["body_steps"]:
            if step_id in state["steps"]:
                state["steps"][step_id].update({
                    "state": StepState.PENDING.value,
                    "started_at": None,
                    "completed_at": None,
                    "token": None,
                    "outputs": [],
                    "validation_result": None,
                    "error": None,
                    "loop_iteration": loop["current_iteration"],
                    "loop_max": loop["max_iterations"]
                })

        state["run_state"] = RunState.LOOPING.value
        self._save_state()
        return True, None

    def complete_loop_iteration(self, loop_id: str, continue_loop: bool = False) -> Tuple[bool, Optional[str]]:
        """完成当前循环迭代

        Args:
            loop_id: 循环 ID
            continue_loop: 是否继续下一轮迭代
        """
        state = self.load()

        if loop_id not in state.get("loops", {}):
            return False, f"Loop not found: {loop_id}"

        loop = state["loops"][loop_id]

        if loop["status"] != "running":
            return False, f"Loop {loop_id} is not running"

        if continue_loop:
            if loop["current_iteration"] >= loop["max_iterations"]:
                loop["status"] = "max_reached"
                state["run_state"] = RunState.RUNNING.value
                self._save_state()
                return False, f"Loop {loop_id} reached max iterations ({loop['max_iterations']})"

            # 继续下一轮 - 重置步骤
            loop["current_iteration"] += 1
            loop["last_iteration_at"] = datetime.now().isoformat()

            for step_id in loop["body_steps"]:
                if step_id in state["steps"]:
                    state["steps"][step_id].update({
                        "state": StepState.PENDING.value,
                        "started_at": None,
                        "completed_at": None,
                        "loop_iteration": loop["current_iteration"]
                    })
        else:
            # 循环完成
            loop["status"] = "completed"
            state["run_state"] = RunState.RUNNING.value

        self._save_state()
        return True, None

    def get_loop_status(self, loop_id: str) -> Optional[Dict]:
        """获取循环状态"""
        state = self.load()
        return state.get("loops", {}).get(loop_id)

    def evaluate_loop_condition(self, loop_id: str, context: Dict = None) -> bool:
        """评估循环条件

        在测试流程中，条件可能是: "open_bugs.count > 0"

        Args:
            loop_id: 循环 ID
            context: 条件评估的上下文 (如: {"open_bugs": {"count": 5}})
        """
        state = self.load()
        loop = state.get("loops", {}).get(loop_id)
        if not loop:
            return False

        condition = loop.get("condition", "false")
        ctx = context or {}

        try:
            # 简单的条件评估
            # 支持: open_bugs.count > 0, cycle < max_cycles
            # 替换常用变量
            expr = condition
            expr = expr.replace("open_bugs.count", str(ctx.get("open_bugs", {}).get("count", 0)))
            expr = expr.replace("cycle", str(loop["current_iteration"]))
            expr = expr.replace("max_cycles", str(loop["max_iterations"]))

            # 安全评估
            result = eval(expr, {"__builtins__": {}}, {})
            return bool(result)
        except Exception:
            return False

    # ============================================
    # 测试流程扩展: 外部事件等待
    # ============================================

    def start_external_wait(
        self,
        step_id: str,
        event_type: str,
        timeout: str = "48h",
        timeout_action: str = "escalate",
        notify_channels: List[str] = None
    ) -> Tuple[bool, str]:
        """开始等待外部事件

        测试流程中用于等待开发修复等外部事件。

        Args:
            step_id: 步骤 ID
            event_type: 事件类型 (如: "fix_version_submitted")
            timeout: 超时时间
            timeout_action: 超时动作
            notify_channels: 通知渠道

        Returns:
            (success, wait_id)
        """
        state = self.load()

        if step_id not in state["steps"]:
            return False, f"Step not found: {step_id}"

        wait_id = f"WAIT-{step_id}-{datetime.now().strftime('%H%M%S')}"

        external_wait = {
            "wait_id": wait_id,
            "step_id": step_id,
            "event_type": event_type,
            "timeout": timeout,
            "timeout_action": timeout_action,
            "notify_channels": notify_channels or [],
            "triggered_at": datetime.now().isoformat(),
            "resolved_at": None,
            "resolved_by": None,
            "event_data": None,
            "status": "waiting"
        }

        state["external_waits"][wait_id] = external_wait

        # 更新步骤状态
        state["steps"][step_id].update({
            "state": StepState.WAITING_EXTERNAL.value,
            "waiting_for_event": event_type,
            "wait_timeout": timeout
        })

        state["run_state"] = RunState.WAITING_EXTERNAL.value
        self._save_state()

        return True, wait_id

    def resolve_external_wait(
        self,
        wait_id: str,
        resolved_by: str,
        event_data: Dict = None
    ) -> Tuple[bool, Optional[str]]:
        """解决外部等待

        当外部事件发生时调用此方法 (如: 开发提交了修复版本)。

        Args:
            wait_id: 等待 ID
            resolved_by: 解决者
            event_data: 事件携带的数据
        """
        state = self.load()

        if wait_id not in state.get("external_waits", {}):
            return False, f"Wait not found: {wait_id}"

        wait = state["external_waits"][wait_id]

        if wait["status"] != "waiting":
            return False, f"Wait {wait_id} is not in waiting status"

        wait.update({
            "resolved_at": datetime.now().isoformat(),
            "resolved_by": resolved_by,
            "event_data": event_data,
            "status": "resolved"
        })

        # 更新步骤状态为可继续
        step_id = wait["step_id"]
        if step_id in state["steps"]:
            state["steps"][step_id].update({
                "state": StepState.COMPLETED.value,
                "completed_at": datetime.now().isoformat(),
                "waiting_for_event": None
            })

        # 检查是否还有其他等待中的事件
        has_waiting = any(
            w["status"] == "waiting"
            for w in state.get("external_waits", {}).values()
        )
        if not has_waiting:
            state["run_state"] = RunState.RUNNING.value

        self._save_state()
        return True, None

    def get_pending_external_waits(self) -> List[Dict]:
        """获取所有等待中的外部事件"""
        state = self.load()
        return [
            w for w in state.get("external_waits", {}).values()
            if w["status"] == "waiting"
        ]

    # ============================================
    # 测试流程扩展: Loop Back 支持
    # ============================================

    def loop_back(self, from_step_id: str, target_step_id: str, reason: str = None) -> Tuple[bool, Optional[str]]:
        """回退到之前的步骤

        测试流程中用于: 出测门禁失败 → 回到 bug 修复循环

        Args:
            from_step_id: 当前步骤 ID
            target_step_id: 目标步骤 ID
            reason: 回退原因
        """
        state = self.load()

        if from_step_id not in state["steps"]:
            return False, f"Step not found: {from_step_id}"

        if target_step_id not in state["steps"]:
            return False, f"Target step not found: {target_step_id}"

        # 记录 loop_back 历史
        if "loop_back_history" not in state:
            state["loop_back_history"] = []

        state["loop_back_history"].append({
            "from_step": from_step_id,
            "to_step": target_step_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

        # 重置从目标步骤开始的所有步骤
        steps_to_reset = self._get_steps_after(state, target_step_id)

        for step_id in steps_to_reset:
            if step_id in state["steps"]:
                state["steps"][step_id].update({
                    "state": StepState.PENDING.value,
                    "started_at": None,
                    "completed_at": None,
                    "outputs": [],
                    "validation_result": None,
                    "error": None
                })

        # 如果目标在循环内，重新激活循环
        for loop_id, loop in state.get("loops", {}).items():
            if target_step_id in loop.get("body_steps", []):
                loop["status"] = "running"
                break

        state["current_step"] = target_step_id
        state["run_state"] = RunState.RUNNING.value
        self._save_state()

        return True, None

    def _get_steps_after(self, state: Dict, start_step_id: str) -> List[str]:
        """获取指定步骤之后的所有步骤 (包括自身)"""
        all_steps = list(state["steps"].keys())
        try:
            start_idx = all_steps.index(start_step_id)
            return all_steps[start_idx:]
        except ValueError:
            return [start_step_id]

    def get_summary(self) -> Dict:
        """获取执行摘要 (增强版: 包含循环和外部等待)"""
        state = self.load()

        step_counts = {}
        for step in state["steps"].values():
            s = step["state"]
            step_counts[s] = step_counts.get(s, 0) + 1

        gate_counts = {"pending": 0, "approved": 0, "rejected": 0}
        for gate in state.get("gates", {}).values():
            s = gate["status"]
            gate_counts[s] = gate_counts.get(s, 0) + 1

        # 新增: 循环状态
        loop_summary = {}
        for loop_id, loop in state.get("loops", {}).items():
            loop_summary[loop_id] = {
                "iteration": loop["current_iteration"],
                "max": loop["max_iterations"],
                "status": loop["status"]
            }

        # 新增: 外部等待状态
        pending_waits = self.get_pending_external_waits()

        return {
            "run_id": state["run_id"],
            "run_state": state["run_state"],
            "current_step": state.get("current_step"),
            "step_counts": step_counts,
            "gate_counts": gate_counts,
            "ready_steps": self.get_ready_steps(),
            "pending_gates": [g.gate_id for g in self.get_pending_gates()],
            "created_at": state["created_at"],
            "updated_at": state["updated_at"],
            "next_step_info": self.get_next_step_info(),
            # 新增
            "loops": loop_summary,
            "pending_external_waits": [w["wait_id"] for w in pending_waits]
        }
