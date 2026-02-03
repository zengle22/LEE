#!/usr/bin/env python3
"""
测试 LEE Orchestrator API

验证：
1. TemplateManager 能正确加载 product-to-dev 模板
2. API 能正确创建工作流
3. API 能正确执行步骤
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.api import (
    api_get_state,
    api_create_workflow,
    api_list_ready_steps,
)


async def test_template_manager():
    """测试模板管理器"""
    print("=" * 60)
    print("测试 1: TemplateManager")
    print("=" * 60)

    # 创建模板管理器
    spec_root = Path(__file__).parent / "spec-global"
    template_manager = TemplateManager(str(spec_root))

    # 测试加载 product-to-dev 模板
    template_id = "workflow.product.product_to_dev_pipeline"
    print(f"\n加载模板: {template_id}")

    template = template_manager.get_template(template_id)

    if template:
        print(f"✅ 模板加载成功!")
        print(f"  - ID: {template.id}")
        print(f"  - 名称: {template.name}")
        print(f"  - 层级: {template.level.value}")
        print(f"  - 步骤数: {len(template.steps)}")
        print(f"\n步骤列表:")
        for i, step in enumerate(template.steps[:5]):  # 只显示前 5 个
            print(f"  {i+1}. {step.id} ({step.kind})")
            if step.agent_id:
                print(f"      agent: {step.agent_id}")
            if step.gate_id:
                print(f"      gate: {step.gate_id}")
        if len(template.steps) > 5:
            print(f"  ... 还有 {len(template.steps) - 5} 个步骤")
        return True
    else:
        print(f"❌ 模板加载失败!")
        return False


async def test_api_get_state():
    """测试获取状态 API"""
    print("\n" + "=" * 60)
    print("测试 2: API get_state")
    print("=" * 60)

    project_dir = str(Path(__file__).parent.parent)

    try:
        result = await api_get_state(project_dir)
        print(f"✅ API 调用成功!")
        print(f"  - 工作流数量: {result.get('total', 0)}")
        return True
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_create_workflow():
    """测试创建工作流 API"""
    print("\n" + "=" * 60)
    print("测试 3: API create_workflow")
    print("=" * 60)

    project_dir = str(Path(__file__).parent.parent)

    # 使用完整的模板文件路径
    template_path = str(
        Path(__file__).parent / "spec-global" / "departments" / "prd" /
        "workflows" / "product-to-dev-pipeline" / "v1" / "workflow.yaml"
    )

    try:
        result = await api_create_workflow(
            project_dir=project_dir,
            level="department",
            template_id=template_path,
            data={
                "project_name": "index-indicator",
                "requirement": "指数指标计算系统",
            }
        )
        print(f"✅ 工作流创建成功!")
        print(f"  - workflow_id: {result.get('workflow_id')}")
        print(f"  - level: {result.get('level')}")
        print(f"  - status: {result.get('status')}")
        return result.get('workflow_id')
    except Exception as e:
        print(f"❌ 工作流创建失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_api_list_ready_steps(workflow_id: str):
    """测试列出就绪步骤 API"""
    print("\n" + "=" * 60)
    print("测试 4: API list_ready_steps")
    print("=" * 60)

    project_dir = str(Path(__file__).parent.parent)

    try:
        ready_steps = await api_list_ready_steps(project_dir, workflow_id)
        print(f"✅ API 调用成功!")
        print(f"  - 就绪步骤数: {len(ready_steps)}")
        for step in ready_steps[:3]:
            print(f"    - {step['id']} ({step['kind']})")
        return True
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("LEE Orchestrator API 测试")
    print("=" * 60)

    # 测试 1: 模板管理器
    template_ok = await test_template_manager()
    if not template_ok:
        print("\n⚠️  模板加载失败，后续测试可能会失败")

    # 测试 2: 获取状态
    state_ok = await test_api_get_state()

    # 测试 3: 创建工作流
    workflow_id = await test_api_create_workflow()

    # 测试 4: 列出就绪步骤
    if workflow_id:
        await test_api_list_ready_steps(workflow_id)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
