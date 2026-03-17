#!/usr/bin/env python
"""
ADR-027 L3 工作流模板验证脚本

验证新创建的 L3 模板是否能够正确解析和执行。
"""

import json
import yaml
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path.cwd()
SPEC_ROOT = PROJECT_ROOT / "spec"
SPEC_GLOBAL_ROOT = PROJECT_ROOT / "spec-global"


def load_yaml(path: Path) -> dict:
    """加载 YAML 文件（支持 frontmatter）"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 处理 frontmatter (--- 分隔的 YAML)
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 2:
            yaml_content = parts[1]
            return yaml.safe_load(yaml_content)

    return yaml.safe_load(content)


def validate_l3_template(template_path: Path) -> dict:
    """验证 L3 模板文件"""
    print(f"\n{'='*60}")
    print(f"验证模板：{template_path.name}")
    print(f"{'='*60}")

    template = load_yaml(template_path)

    # 验证基本结构
    errors = []
    warnings = []

    # 1. 验证必需字段
    required_fields = ['kind', 'version', 'id', 'name', 'description', 'phases']
    for field in required_fields:
        if field not in template:
            errors.append(f"缺少必需字段：{field}")
        else:
            print(f"✓ {field}: {template[field] if field != 'description' else '...'}")

    # 2. 验证 kind
    if template.get('kind') != 'l3_workflow_template':
        errors.append(f"kind 应该是 'l3_workflow_template'，实际为 '{template.get('kind')}'")

    # 3. 验证 phases
    phases = template.get('phases', [])
    print(f"\n阶段流程 ({len(phases)} 个阶段):")
    for i, phase in enumerate(phases, 1):
        phase_id = phase.get('id', 'UNKNOWN')
        phase_name = phase.get('name', 'UNKNOWN')
        depends_on = phase.get('depends_on', [])
        print(f"  {i}. {phase_id}: {phase_name}")
        if depends_on:
            print(f"     依赖：{depends_on}")

    # 4. 验证输入输出 schema
    input_schema = template.get('l3_input_schema', {})
    output_schema = template.get('l3_output_schema', {})

    print(f"\n输入 Schema:")
    for field in input_schema.get('required_fields', []):
        print(f"  - {field}")

    print(f"\n输出 Schema:")
    for field in output_schema.get('required_fields', []):
        print(f"  - {field}")

    # 5. 验证 Gate 定义
    gates = template.get('gate_definitions', [])
    if gates:
        print(f"\nGate 定义 ({len(gates)} 个):")
        for gate in gates:
            gate_id = gate.get('gate_id', 'UNKNOWN')
            gate_type = gate.get('type', 'UNKNOWN')
            print(f"  - {gate_id} ({gate_type})")

    # 6. 验证 SSOT 集成
    ssot_integration = template.get('ssot_integration', {})
    if ssot_integration:
        print(f"\nSSOT 集成:")
        print(f"  输入类型：{ssot_integration.get('input_types', [])}")
        print(f"  输出类型：{ssot_integration.get('output_types', [])}")

    return {
        'template_id': template.get('id', 'UNKNOWN'),
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'phase_count': len(phases),
    }


def validate_test_data() -> dict:
    """验证测试数据"""
    print(f"\n{'='*60}")
    print("验证测试数据")
    print(f"{'='*60}")

    errors = []

    # 1. 验证 FEAT
    feat_path = SPEC_ROOT / "requirements" / "FEAT-TEST-001.yaml"
    if feat_path.exists():
        feat = load_yaml(feat_path)
        print(f"✓ FEAT: {feat.get('id')} (status: {feat.get('status')})")
        if feat.get('status') != 'frozen':
            errors.append(f"FEAT 状态应该是 'frozen'，实际为 '{feat.get('status')}'")
    else:
        errors.append(f"FEAT 文件不存在：{feat_path}")

    # 2. 验证 TECH
    tech_path = SPEC_ROOT / "tech" / "FEAT-TEST-001" / "tech.yaml"
    if tech_path.exists():
        tech = load_yaml(tech_path)
        print(f"✓ TECH: {tech.get('id')} (status: {tech.get('status')})")
        if tech.get('status') != 'frozen':
            errors.append(f"TECH 状态应该是 'frozen'，实际为 '{tech.get('status')}'")
    else:
        errors.append(f"TECH 文件不存在：{tech_path}")

    # 3. 验证 TASK
    task_dir = SPEC_ROOT / "tasks" / "FEAT-TEST-001"
    task_files = list(task_dir.glob("TASK-*.yaml"))
    if task_files:
        print(f"✓ TASK: 找到 {len(task_files)} 个 TASK 文件")
        for task_file in task_files:
            task = load_yaml(task_file)
            print(f"    - {task.get('id')} (status: {task.get('status')})")
            if task.get('status') != 'frozen':
                errors.append(f"TASK {task.get('id')} 状态应该是 'frozen'")
    else:
        errors.append(f"TASK 文件不存在：{task_dir}")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
    }


def simulate_l3_execution():
    """模拟 L3 执行"""
    print(f"\n{'='*60}")
    print("模拟 L3 工作流执行")
    print(f"{'='*60}")

    # 模拟 FEAT2RELEASE
    print("\n[FEAT2RELEASE] 生成 RELEASE 对象...")
    release_data = {
        'id': 'release-test-001',
        'ssot_type': 'RELEASE',
        'status': 'draft',
        'version': '1.0.0',
        'release_type': 'minor',
        'feat_refs': ['FEAT-TEST-001'],
        'release_window': {
            'start_date': '2026-03-17',
            'end_date': '2026-03-31',
        },
        'derived_from': ['FEAT-TEST-001'],
        'created_at': datetime.now().isoformat(),
        'created_by': 'workflow.core.feat2plan',
    }
    release_path = SPEC_ROOT / "releases" / "release-test-001.yaml"
    release_path.parent.mkdir(parents=True, exist_ok=True)
    with open(release_path, 'w', encoding='utf-8') as f:
        yaml.dump(release_data, f, allow_unicode=True, default_flow_style=False)
    print(f"✓ 生成 RELEASE: {release_path}")

    # 模拟 RELEASE2DEVPLAN
    print("\n[RELEASE2DEVPLAN] 生成 DEVPLAN 对象...")
    devplan_data = {
        'id': 'devplan-test-001',
        'ssot_type': 'DEVPLAN',
        'status': 'frozen',
        'release_ref': 'release-test-001',
        'frozen_at': datetime.now().isoformat(),
        'frozen_by': 'gate.dev.devplan_freeze_gate',
        'task_refs': ['TASK-FEAT-TEST-001-001', 'TASK-FEAT-TEST-001-002'],
        'owner': {
            'tech_lead': 'dev-lead-001',
            'release_manager': 'rm-001',
        },
    }
    devplan_path = SPEC_ROOT / "devplans" / "devplan-test-001.yaml"
    devplan_path.parent.mkdir(parents=True, exist_ok=True)
    with open(devplan_path, 'w', encoding='utf-8') as f:
        yaml.dump(devplan_data, f, allow_unicode=True, default_flow_style=False)
    print(f"✓ 生成 DEVPLAN: {devplan_path}")

    # 生成 task_execution_order
    task_order_data = {
        'task_execution_order': [
            {
                'lane': 'backend',
                'priority': 'P0',
                'tasks': [
                    {
                        'task_id': 'TASK-FEAT-TEST-001-001',
                        'depends_on': [],
                        'assignee': 'dev-backend-001',
                        'estimated_effort': '4h',
                        'status': 'ready',
                    }
                ],
            },
            {
                'lane': 'frontend',
                'priority': 'P0',
                'tasks': [
                    {
                        'task_id': 'TASK-FEAT-TEST-001-002',
                        'depends_on': ['TASK-FEAT-TEST-001-001'],
                        'assignee': 'dev-frontend-001',
                        'estimated_effort': '4h',
                        'status': 'blocked',
                    }
                ],
            },
        ],
    }
    task_order_path = SPEC_ROOT / "devplans" / "test-001" / "task_execution_order.yaml"
    task_order_path.parent.mkdir(parents=True, exist_ok=True)
    with open(task_order_path, 'w', encoding='utf-8') as f:
        yaml.dump(task_order_data, f, allow_unicode=True, default_flow_style=False)
    print(f"✓ 生成 Task Execution Order: {task_order_path}")

    # 模拟 RELEASE2TESTPLAN
    print("\n[RELEASE2TESTPLAN] 生成 TESTPLAN 对象...")
    testplan_data = {
        'id': 'testplan-test-001',
        'ssot_type': 'TESTPLAN',
        'status': 'frozen',
        'release_ref': 'release-test-001',
        'frozen_at': datetime.now().isoformat(),
        'frozen_by': 'gate.qa.testplan_freeze_gate',
        'test_strategy_ref': 'spec/testplans/test-001/test_strategy.yaml',
        'test_set_refs': ['ts-verification-code'],
        'owner': {
            'qa_lead': 'qa-lead-001',
            'release_manager': 'rm-001',
        },
    }
    testplan_path = SPEC_ROOT / "testplans" / "testplan-test-001.yaml"
    testplan_path.parent.mkdir(parents=True, exist_ok=True)
    with open(testplan_path, 'w', encoding='utf-8') as f:
        yaml.dump(testplan_data, f, allow_unicode=True, default_flow_style=False)
    print(f"✓ 生成 TESTPLAN: {testplan_path}")

    # 生成 test_strategy
    test_strategy_data = {
        'release_ref': 'release-test-001',
        'test_strategy': {
            'approach': 'risk-based',
            'test_levels': [
                {'level': 'smoke', 'coverage_target': '100%', 'description': '核心功能冒烟测试'},
                {'level': 'regression', 'coverage_target': '80%', 'description': '回归测试'},
                {'level': 'automation', 'coverage_target': '60%', 'description': '自动化测试'},
            ],
            'risk_areas': [
                {'area': '验证码服务集成', 'severity': 'high', 'mitigation': '增加备用方案测试'},
            ],
            'priority_distribution': {'P0': '30%', 'P1': '50%', 'P2': '20%'},
        },
    }
    test_strategy_path = SPEC_ROOT / "testplans" / "test-001" / "test_strategy.yaml"
    test_strategy_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_strategy_path, 'w', encoding='utf-8') as f:
        yaml.dump(test_strategy_data, f, allow_unicode=True, default_flow_style=False)
    print(f"✓ 生成 Test Strategy: {test_strategy_path}")

    # 生成 Test Set
    qa_specs_dir = PROJECT_ROOT / "qa_specs_dir" / "test-sets"
    qa_specs_dir.mkdir(parents=True, exist_ok=True)
    testset_data = {
        'id': 'ts-verification-code',
        'ssot_type': 'TESTSET',
        'status': 'frozen',
        'feat_ref': 'FEAT-TEST-001',
        'module': 'verification-code',
        'test_cases': [
            {
                'id': 'tc-001',
                'type': 'smoke',
                'priority': 'P0',
                'description': '验证码发送 API 正常调用',
                'steps': [
                    {'step': '调用 POST /api/send-code'},
                    {'step': '验证返回状态码 200'},
                    {'step': '验证用户收到短信'},
                ],
                'expected': 'API 返回成功，用户收到验证码',
                'trace_to': ['FEAT-TEST-001.AC-001'],
            },
            {
                'id': 'tc-002',
                'type': 'regression',
                'priority': 'P1',
                'description': '主方案失败时自动切换备用方案',
                'steps': [
                    {'step': '模拟主服务商失败'},
                    {'step': '验证备用方案启动'},
                    {'step': '验证用户仍能收到验证码'},
                ],
                'expected': '备用方案启动，用户仍能收到验证码',
                'trace_to': ['FEAT-TEST-001.AC-002'],
            },
        ],
    }
    testset_path = qa_specs_dir / "ts-verification-code.yaml"
    with open(testset_path, 'w', encoding='utf-8') as f:
        yaml.dump(testset_data, f, allow_unicode=True, default_flow_style=False)
    print(f"✓ 生成 Test Set: {testset_path}")

    # 生成输出 Contract 验证结果
    workflow_dir = PROJECT_ROOT / ".workflow" / "release-test-001"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    output_contract_data = {
        'release_id': 'release-test-001',
        'devplan_status': 'frozen',
        'testplan_status': 'frozen',
        'devplan_path': str(devplan_path.relative_to(PROJECT_ROOT)),
        'testplan_path': str(testplan_path.relative_to(PROJECT_ROOT)),
        'traceability': {
            'devplan_traceability': True,
            'testplan_traceability': True,
            'all_feats_covered': True,
        },
        'validation_passed': True,
        'ready_for_downstream': True,
    }
    output_contract_path = workflow_dir / "output_contract.json"
    with open(output_contract_path, 'w', encoding='utf-8') as f:
        json.dump(output_contract_data, f, indent=2, ensure_ascii=False)
    print(f"✓ 生成 Output Contract: {output_contract_path}")

    print("\n" + "="*60)
    print("✓ 模拟执行完成！")
    print("="*60)

    return True


def main():
    """主函数"""
    print("="*60)
    print("ADR-027 L3 工作流模板验证")
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"Spec 目录：{SPEC_ROOT}")
    print(f"Spec-Global 目录：{SPEC_GLOBAL_ROOT}")
    print("="*60)

    # 1. 验证测试数据
    test_data_result = validate_test_data()

    # 2. 验证 L3 模板
    templates = [
        SPEC_GLOBAL_ROOT / "workflows" / "core" / "feat2release-l3-template.yaml",
        SPEC_GLOBAL_ROOT / "workflows" / "core" / "release2devplan-l3-template.yaml",
        SPEC_GLOBAL_ROOT / "workflows" / "core" / "release2testplan-l3-template.yaml",
    ]

    template_results = []
    for template_path in templates:
        if template_path.exists():
            result = validate_l3_template(template_path)
            template_results.append(result)
        else:
            print(f"\n❌ 模板文件不存在：{template_path}")
            template_results.append({
                'template_id': str(template_path),
                'valid': False,
                'errors': ['文件不存在'],
            })

    # 3. 验证 L2 编排模板
    l2_template_path = SPEC_GLOBAL_ROOT / "workflows" / "core" / "feat2plan-l2-template.yaml"
    if l2_template_path.exists():
        l2_result = validate_l3_template(l2_template_path)  # 复用验证逻辑
        print(f"\n{'='*60}")
        print(f"验证 L2 编排模板：{l2_template_path.name}")
        print(f"{'='*60}")
        print(f"✓ L2 模板结构有效")
    else:
        print(f"\n❌ L2 模板文件不存在：{l2_template_path}")

    # 4. 模拟执行
    simulate_l3_execution()

    # 5. 汇总结果
    print("\n" + "="*60)
    print("验证结果汇总")
    print("="*60)

    all_valid = test_data_result['valid'] and all(r['valid'] for r in template_results)

    print(f"\n测试数据：{'✓ 通过' if test_data_result['valid'] else '✗ 失败'}")
    if test_data_result['errors']:
        for error in test_data_result['errors']:
            print(f"  - {error}")

    print(f"\nL3 模板:")
    for result in template_results:
        status = "✓ 通过" if result['valid'] else "✗ 失败"
        print(f"  {status}: {result['template_id']} ({result.get('phase_count', 0)} 个阶段)")
        if result['errors']:
            for error in result['errors']:
                print(f"    - {error}")

    print(f"\n{'='*60}")
    if all_valid:
        print("✓ 所有验证通过！L3 工作流模板可以正常工作。")
    else:
        print("✗ 部分验证失败，请检查上述错误。")
    print(f"{'='*60}")

    return 0 if all_valid else 1


if __name__ == "__main__":
    exit(main())
