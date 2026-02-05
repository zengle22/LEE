"""
LEE Orchestrator - P1 完整演示

演示 spec-global 工作流的完整执行流程，包括：
1. 工作流加载和解析
2. 状态机执行
3. 条件评估
4. 门禁评估
5. 人工审批流程
"""

import json
import tempfile
from pathlib import Path

# 导入 P1 实现的模块
from lee.orchestrator.execution.spec_global_parser import SpecGlobalParser
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.execution.state_machine_executor import StateMachineExecutor, StateTransitionResult
from lee.orchestrator.execution.gate_engine import GateEngine, GateVerdict
from lee.orchestrator.execution.condition_engine import ConditionEngine
from lee.orchestrator.execution.human_approval import HumanApprovalExecutor, ApprovalStatus


class WorkflowDemo:
    """工作流演示类"""

    def __init__(self):
        """初始化演示"""
        print("=" * 70)
        print("LEE Orchestrator - P1 完整演示")
        print("=" * 70)

        # 初始化引擎
        self.parser = SpecGlobalParser()
        self.state_executor = None
        self.gate_engine = GateEngine()
        self.condition_engine = ConditionEngine()
        self.approval_executor = None

        # 执行上下文
        self.context = {
            "inputs": {
                "prd": {
                    "frozen": True,
                    "features": [
                        {"id": "F001", "name": "用户登录", "acceptance_criteria": ["Given用户在登录页", "When输入正确凭证", "Then成功登录"]},
                        {"id": "F002", "name": "密码重置", "acceptance_criteria": ["Given用户忘记密码", "When点击重置链接", "Then收到重置邮件"]},
                        {"id": "F003", "name": "个人资料编辑", "acceptance_criteria": ["Given用户已登录", "When修改资料", "Then保存成功"]},
                        {"id": "F004", "name": "数据导出", "acceptance_criteria": ["Given用户有数据权限", "When选择导出", "Then下载文件"]},
                        {"id": "F005", "name": "系统设置", "acceptance_criteria": ["Given用户是管理员", "When修改设置", "Then配置生效"]},
                    ]
                },
                "tech_arch": {
                    "frozen": True,
                    "components": [
                        {"id": "C001", "name": "AuthService", "type": "service"},
                        {"id": "C002", "name": "UserService", "type": "service"},
                        {"id": "C003", "name": "DataExportService", "type": "service"},
                    ]
                },
                "ui_prototype": {
                    "frozen": True,
                    "pages": [
                        {"id": "P001", "name": "登录页", "path": "/login"},
                        {"id": "P002", "name": "主页", "path": "/home"},
                        {"id": "P003", "name": "个人中心", "path": "/profile"},
                    ]
                },
                "ui_page": {
                    "pages": ["登录页", "主页", "个人中心"]
                }
            },
            "feature_coverage": 92,
            "consistency_matrix": {
                "prd_vs_arch": True,
                "prd_vs_ui": True,
                "arch_vs_ui": True,
                "conflicts": []
            },
            "document_completeness": 95,
            "s2_1": {
                "validation_result": "passed",
                "consistency_check": "no_conflicts"
            },
            "s3_1": {
                "feature_to_component": {
                    "F001": ["C001", "C002"],
                    "F002": ["C002"],
                    "F003": ["C002"],
                    "F004": ["C003"],
                    "F005": ["C001"]
                },
                "coverage_gaps": []
            },
            "test_case_design": {
                "total_cases": 45,
                "branch_coverage": 88,
                "quality_score": 8.5
            }
        }

    def demo_1_parse_workflow(self):
        """演示 1: 解析 spec-global 工作流"""
        print("\n" + "=" * 70)
        print("【演示 1】解析 spec-global 工作流")
        print("=" * 70)

        # 解析工作流
        workflow_ir = self.parser.parse_workflow_file(
            'spec-global/departments/qa/workflows/test-case-design-pipeline/v1/workflow.yaml'
        )

        print(f"\n✓ 工作流加载成功")
        print(f"  ID: {workflow_ir.id}")
        print(f"  名称: {workflow_ir.name}")
        print(f"  所有者: {workflow_ir.owner}")
        print(f"  标签: {', '.join(workflow_ir.tags)}")

        print(f"\n  契约:")
        print(f"    输入: {len(workflow_ir.inputs)} 个")
        for contract in workflow_ir.inputs:
            print(f"      - {contract.contract_id}: {contract.description}")
        print(f"    输出: {len(workflow_ir.outputs)} 个")
        for contract in workflow_ir.outputs:
            print(f"      - {contract.contract_id}: {contract.description}")

        print(f"\n  状态机:")
        print(f"    状态数量: {len(workflow_ir.state_machine.states)}")
        print(f"    初始状态: {workflow_ir.state_machine.initial_state}")
        print(f"    状态: {' → '.join(workflow_ir.state_machine.states[:5])} ...")

        print(f"\n  阶段 (Stages): {len(workflow_ir.stages)} 个")
        for stage in workflow_ir.stages:
            print(f"    - {stage.id}: {stage.name} ({len(stage.steps)} 步)")

        print(f"\n  门禁 (Gates): {len(workflow_ir.gates)} 个")
        for gate_id, gate in workflow_ir.gates.items():
            print(f"    - {gate_id}: {gate.name}")
            print(f"      Mandatory: {len(gate.mandatory_criteria)}, Threshold: {len(gate.threshold_criteria)}")

        print(f"\n  人类介入: {len(workflow_ir.human_in_the_loop)} 个")
        for hitl in workflow_ir.human_in_the_loop:
            print(f"    - {hitl.name}: {hitl.type} @ {hitl.stage}/{hitl.step}")

        # 创建状态机执行器
        self.state_executor = StateMachineExecutor(workflow_ir)

        return workflow_ir

    def demo_2_state_machine(self):
        """演示 2: 状态机执行"""
        print("\n" + "=" * 70)
        print("【演示 2】状态机执行")
        print("=" * 70)

        print(f"\n当前状态: {self.state_executor.current_state}")

        # 模拟状态转换
        transitions = [
            ("workflow_started", "工作流启动"),
            ("input_gate_pass", "输入门禁通过"),
            ("requirement_aligned", "需求对齐完成"),
            ("feature_calibrated", "功能校准完成"),
        ]

        print("\n状态转换序列:")
        for trigger, description in transitions:
            print(f"\n  触发: {trigger} ({description})")
            result = self.state_executor.transition(trigger, {"note": description})
            print(f"  结果: {result.value}")
            print(f"  新状态: {self.state_executor.current_state}")

            # 检查是否是终态
            if self.state_executor.is_terminal:
                print(f"  → 到达终态")
                break

            # 显示可用的下一步转换
            valid_transitions = self.state_executor.get_valid_transitions()
            if valid_transitions:
                print(f"  可用转换: {', '.join([t.to_state for t in valid_transitions])}")

        # 显示状态摘要
        summary = self.state_executor.get_state_summary()
        print(f"\n状态摘要:")
        print(f"  总转换次数: {summary['total_transitions']}")
        print(f"  已用时间: {summary['elapsed_time']:.3f} 秒")
        print(f"  状态时间分布:")
        for state, time_spent in summary['state_times'].items():
            print(f"    {state}: {time_spent:.3f} 秒")

    def demo_3_condition_engine(self):
        """演示 3: 条件引擎"""
        print("\n" + "=" * 70)
        print("【演示 3】条件引擎评估")
        print("=" * 70)

        conditions = [
            ("简单条件", "$inputs.prd.frozen == True", None),
            ("数值比较", "feature_coverage >= 80", None),
            ("逻辑与", "$inputs.prd.frozen == True && $inputs.tech_arch.frozen == True", None),
            ("逻辑或", "feature_coverage >= 90 || feature_coverage >= 80", None),
            ("逻辑非", "not $consistency_matrix.conflicts", None),
            ("嵌套条件", "($inputs.prd.frozen == True || $inputs.tech_arch.frozen == True) && feature_coverage >= 80", None),
        ]

        for name, condition, _ in conditions:
            try:
                result = self.condition_engine.evaluate(condition, self.context)
                status = "✓" if result else "✗"
                print(f"\n  {status} [{name}]")
                print(f"    条件: {condition}")
                print(f"    结果: {result}")
            except Exception as e:
                print(f"\n  ✗ [{name}]")
                print(f"    条件: {condition}")
                print(f"    错误: {e}")

        # 批量条件评估
        print(f"\n批量条件评估 (AND 逻辑):")
        batch_conditions = [
            "$inputs.prd.frozen == True",
            "$inputs.tech_arch.frozen == True",
            "$inputs.ui_prototype.frozen == True",
        ]
        result = self.condition_engine.evaluate_batch(batch_conditions, self.context, logic="all")
        print(f"  条件: 所有输入契约都已冻结")
        print(f"  结果: {result}")

    def demo_4_gate_evaluation(self):
        """演示 4: 门禁评估"""
        print("\n" + "=" * 70)
        print("【演示 4】门禁评估")
        print("=" * 70)

        workflow_ir = self.state_executor.workflow_ir

        # 评估 design_input_gate
        print("\n[门禁 1] Design Input Gate")
        gate = workflow_ir.gates['design_input_gate']

        result = self.gate_engine.evaluate_gate(gate, self.context)

        print(f"  门禁 ID: {result.gate_id}")
        print(f"  门禁名称: {result.gate_name}")
        print(f"  判定结果: {result.verdict.value.upper()}")
        print(f"  Mandatory 规则通过: {result.mandatory_passed}")
        print(f"  Threshold 得分: {result.threshold_score}")

        if result.failed_rules:
            print(f"  失败规则: {', '.join(result.failed_rules[:5])}...")

        # 显示前几个规则结果
        print(f"\n  规则评估详情 (前5条):")
        for i, rule_result in enumerate(result.rule_results[:5]):
            status = "✓" if rule_result.passed else "✗"
            print(f"    {status} {rule_result.rule_name}")
            if rule_result.error_message:
                print(f"       错误: {rule_result.error_message}")

        # 评估 test_case_review_gate
        print(f"\n[门禁 2] Test Case Review Gate")
        gate2 = workflow_ir.gates['test_case_review_gate']

        result2 = self.gate_engine.evaluate_gate(gate2, self.context)

        print(f"  门禁 ID: {result2.gate_id}")
        print(f"  门禁名称: {result2.gate_name}")
        print(f"  判定结果: {result2.verdict.value.upper()}")

    def demo_5_human_approval(self):
        """演示 5: 人工审批流程"""
        print("\n" + "=" * 70)
        print("【演示 5】人工审批流程")
        print("=" * 70)

        # 创建临时存储
        temp_dir = tempfile.mkdtemp()
        storage_path = f"{temp_dir}/approvals.json"

        self.approval_executor = HumanApprovalExecutor(storage_path)

        # 创建审批请求
        print("\n[创建审批请求]")
        request = self.approval_executor.create_request(
            gate_id="gate.qa.test_case_review_gate",
            gate_name="Test Case Review Gate",
            workflow_id=self.state_executor.workflow_ir.id,
            workflow_run_id="demo-run-001",
            stage_id="s6_test_case_review",
            step_id="s6_2_human_review",
            required_approvers=[
                {"id": "user-qa-lead", "name": "张三", "role": "qa_lead"},
                {"id": "user-tech-lead", "name": "李四", "role": "tech_lead"},
            ],
            optional_approvers=[
                {"id": "user-pm", "name": "王五", "role": "pm"},
            ],
            approval_sla=72,
            approval_criteria={
                "coverage_completeness": {"threshold": 90, "metric": "feature_coverage_percentage"},
                "case_quality": {"threshold": 8, "metric": "average_case_quality_score"},
                "traceability": {"threshold": 100, "metric": "requirement_traceability_percentage"}
            },
            context_data=self.context
        )

        print(f"  请求 ID: {request.request_id}")
        print(f"  门禁: {request.gate_name}")
        print(f"  状态: {request.status.value}")
        print(f"  必需审批人: {len(request.required_approvers)} 位")
        for approver in request.required_approvers:
            print(f"    - {approver.get('name')} ({approver.get('role')})")
        print(f"  可选审批人: {len(request.optional_approvers)} 位")
        print(f"  审批 SLA: {request.approval_sla} 小时")
        print(f"  截止时间: {request.deadline}")

        # 提交审批决策
        print(f"\n[提交审批决策]")

        # 第一个批准
        decision1 = self.approval_executor.submit_decision(
            request_id=request.request_id,
            approver="user-qa-lead",
            approver_role="qa_lead",
            decision=ApprovalStatus.APPROVED,
            comments="测试用例覆盖度达标（92%），质量评分8.5分，通过审批。",
            metadata={"review_time": "30min"}
        )
        print(f"  决策 1: {decision1.approver} ({decision1.approver_role})")
        print(f"    决策: {decision1.decision.value}")
        print(f"    评论: {decision1.comments}")

        # 检查状态
        updated_request = self.approval_executor.get_request(request.request_id)
        print(f"  当前状态: {updated_request.status.value}")

        # 如果需要更多批准，提交第二个
        if updated_request.status == ApprovalStatus.PENDING:
            decision2 = self.approval_executor.submit_decision(
                request_id=request.request_id,
                approver="user-tech-lead",
                approver_role="tech_lead",
                decision=ApprovalStatus.APPROVED,
                comments="技术架构验证通过，测试用例覆盖所有组件。"
            )
            print(f"\n  决策 2: {decision2.approver} ({decision2.approver_role})")
            print(f"    决策: {decision2.decision.value}")

            # 最终状态
            final_request = self.approval_executor.get_request(request.request_id)
        else:
            print(f"\n  → 审批已通过（min_required=1）")
            final_request = updated_request
        print(f"\n[最终状态]")
        print(f"  状态: {final_request.status.value.upper()}")
        print(f"  完成时间: {final_request.completed_at}")

        # 审批摘要
        summary = self.approval_executor.get_summary()
        print(f"\n[审批摘要]")
        print(f"  总请求数: {summary['total']}")
        print(f"  已批准: {summary['approved']}")
        print(f"  已拒绝: {summary['rejected']}")
        print(f"  待处理: {summary['pending']}")

        # 持久化测试
        print(f"\n[持久化测试]")
        new_executor = HumanApprovalExecutor(storage_path)
        loaded_request = new_executor.get_request(request.request_id)
        print(f"  ✓ 从存储加载请求: {loaded_request.request_id == request.request_id}")
        print(f"  ✓ 状态一致: {loaded_request.status == final_request.status}")

        # 清理
        import shutil
        shutil.rmtree(temp_dir)

    def demo_6_integration(self):
        """演示 6: 集成演示"""
        print("\n" + "=" * 70)
        print("【演示 6】端到端集成演示")
        print("=" * 70)

        print("\n模拟完整的测试用例设计工作流执行:")

        # 重置状态机
        workflow_ir = self.parser.parse_workflow_file(
            'spec-global/departments/qa/workflows/test-case-design-pipeline/v1/workflow.yaml'
        )
        self.state_executor = StateMachineExecutor(workflow_ir)

        steps = [
            ("INIT", "workflow_started", "启动工作流", None),
            ("INPUT_VALIDATION", "input_gate_pass", "输入门禁通过", "$inputs.prd.frozen == True"),
            ("REQUIREMENT_ALIGNMENT", "requirement_aligned", "需求对齐完成", "$consistency_matrix.conflicts == 0"),
            ("FEATURE_CALIBRATION", "feature_calibrated", "功能校准完成", "feature_coverage >= 80"),
        ]

        print("\n执行流程:")
        for expected_state, trigger, description, condition in steps:
            # 检查条件
            if condition:
                condition_result = self.condition_engine.evaluate(condition, self.context)
                print(f"\n  [{self.state_executor.current_state}]")
                print(f"    → 条件检查: {condition}")
                print(f"    → 结果: {condition_result}")
                if not condition_result:
                    print(f"    → 条件不满足，流程终止")
                    break

            # 执行状态转换
            result = self.state_executor.transition(trigger, {"description": description})
            print(f"  [{expected_state}]")
            print(f"    → 触发: {trigger}")
            print(f"    → 描述: {description}")
            print(f"    → 结果: {result.value}")

            # 如果到达设计输入门禁，执行门禁评估
            if expected_state == "INPUT_VALIDATION":
                gate = workflow_ir.gates['design_input_gate']
                gate_result = self.gate_engine.evaluate_gate(gate, self.context)
                print(f"\n    → 门禁评估: {gate.name}")
                print(f"    → 判定: {gate_result.verdict.value}")
                if gate_result.verdict == GateVerdict.FAIL:
                    print(f"    → 门禁失败，流程阻塞")
                    break

        # 显示最终状态
        summary = self.state_executor.get_state_summary()
        print(f"\n执行摘要:")
        print(f"  当前状态: {self.state_executor.current_state}")
        print(f"  是否终态: {summary['is_terminal']}")
        print(f"  总转换: {summary['total_transitions']} 次")
        print(f"  运行时间: {summary['elapsed_time']:.3f} 秒")

    def run(self):
        """运行完整演示"""
        try:
            self.demo_1_parse_workflow()
            self.demo_2_state_machine()
            self.demo_3_condition_engine()
            self.demo_4_gate_evaluation()
            self.demo_5_human_approval()
            self.demo_6_integration()

            print("\n" + "=" * 70)
            print("演示完成！所有 P1 功能正常运行 ✓")
            print("=" * 70)

        except Exception as e:
            print(f"\n演示出错: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    demo = WorkflowDemo()
    demo.run()
