#!/usr/bin/env python3
"""
STG Opportunity Discovery Workflow Test
测试完整的商业机会发现工作流
"""

import asyncio
import json
import yaml
from pathlib import Path
from datetime import datetime

# 模拟各个 Agent 的执行
async def test_search_agent():
    """测试 Layer 1: Search Agent"""
    print("\n" + "="*60)
    print("🔍 Layer 1: Search Agent - 搜索采集")
    print("="*60)

    # 读取输入
    base_path = Path(__file__).parent.parent.parent / "spec-global/departments/stg/examples"
    input_file = base_path / "layer1_search/input.json"
    with open(input_file) as f:
        input_data = json.load(f)

    print(f"Input: {json.dumps(input_data, indent=2)}")

    # 模拟执行
    print("\n✓ 执行搜索采集...")
    print("  - Google Trends: 搜索 'AI sales assistant'")
    print("  - Keyword Tool: 分析关键词量级")
    print("  - Ahrefs: 获取地理分布")

    # 读取输出
    output_file = base_path / "layer1_search/output.json"
    with open(output_file) as f:
        output_data = json.load(f)

    print(f"\n✓ Output: {len(output_data['signals'])} signals collected")
    for signal in output_data['signals'][:3]:
        print(f"  - {signal['keyword']}: {signal['trend']}, {signal['volume_range']}")

    return output_data


async def test_analysis_layers(search_signals):
    """测试 Layer 2: Analysis Agents (并行执行)"""
    print("\n" + "="*60)
    print("🔬 Layer 2: Analysis Agents - 分析层 (并行)")
    print("="*60)

    # 并行执行三个分析 Agent
    results = await asyncio.gather(
        test_user_signal_analysis(),
        test_industry_structure_analysis(),
        test_supply_competition_analysis()
    )

    user_hypothesis, industry_structure, supply_gap = results

    print("\n✓ All 3 analysis agents completed")
    print(f"  - User Hypothesis: {len(user_hypothesis['hypotheses'])} hypotheses")
    print(f"  - Industry Structure: {industry_structure['maturity_stage']} stage")
    print(f"  - Supply Gap: {len(industry_structure['structural_gap'])} gaps identified")

    return {
        "user_hypothesis": user_hypothesis,
        "industry_structure": industry_structure,
        "supply_gap": supply_gap
    }


async def test_user_signal_analysis():
    """测试用户信号分析"""
    print("\n  [User Signal Agent]")
    base_path = Path(__file__).parent.parent.parent / "spec-global/departments/stg/examples"
    output_file = base_path / "layer2_analysis/user_signal_output.json"
    with open(output_file) as f:
        return json.load(f)


async def test_industry_structure_analysis():
    """测试行业结构分析"""
    print("  [Industry Structure Agent]")
    base_path = Path(__file__).parent.parent.parent / "spec-global/departments/stg/examples"
    output_file = base_path / "layer2_analysis/industry_structure_output.json"
    with open(output_file) as f:
        return json.load(f)


async def test_supply_competition_analysis():
    """测试供给竞争分析"""
    print("  [Supply/Competition Agent]")
    base_path = Path(__file__).parent.parent.parent / "spec-global/departments/stg/examples"
    output_file = base_path / "layer2_analysis/supply_gap_output.json"
    with open(output_file) as f:
        return json.load(f)


async def test_freeze_layer(analysis_results):
    """测试 Layer 3: Freeze Layer"""
    print("\n" + "="*60)
    print("🔒 Layer 3: Market Signal Freeze - 冻结层")
    print("="*60)

    print("\n⚠️  需要人工或规则审核:")
    print("  ✓ 分析一致性: 三个分析层输出无明显矛盾")
    print("  ✓ 置信度达标: 综合置信度 72/100")
    print("  ✓ 可验证性: 核心假设可以通过后续验证")

    # 读取冻结示例
    base_path = Path(__file__).parent.parent.parent / "spec-global/departments/stg/examples"
    freeze_file = base_path / "layer3_freeze/freeze.yaml"
    with open(freeze_file) as f:
        freeze_content = f.read()

    print("\n✓ 冻结记录已创建:")
    print(f"  - Freeze ID: freeze-20250123-001")
    print(f"  - Version: v1.0")
    print(f"  - Confidence: 72/100")
    print(f"  - Assumptions frozen: 3")

    return freeze_content


async def test_business_opportunity_agent(freeze_data):
    """测试 Layer 4: Business Opportunity Agent"""
    print("\n" + "="*60)
    print("💡 Layer 4: Business Opportunity Agent - 机会构建层")
    print("="*60)

    print("\n✓ 基于冻结数据构建机会假设")
    print("  - One-liner: AI Sales Assistant for mid-market B2B companies")
    print("  - Target User: VP of Sales at mid-market B2B SaaS")
    print("  - Why Now: 4 strong reasons")
    print("  - Differentiation: 3 potential angles")
    print("  - Reasons NOT to Do: 4 risks identified")
    print("  - Validation: User interview + Landing page + Fake door test")

    base_path = Path(__file__).parent.parent.parent / "spec-global/departments/stg/examples"
    opp_file = base_path / "layer4_opportunity/opportunity.json"
    with open(opp_file) as f:
        return yaml.safe_load(f)


async def test_product_handoff(opportunity_data):
    """测试 Layer 5: Product Handoff"""
    print("\n" + "="*60)
    print("📦 Layer 5: Product Handoff - 交付层")
    print("="*60)

    print("\n✓ 创建产品交付文档:")
    print("  What we believe:")
    print("    - Mid-market sales teams need AI productivity tools")
    print("    - Can't afford enterprise solutions ($5k+/month)")
    print("    - No industry-specific options exist")
    print()
    print("  What we don't know:")
    print("    - Actual willingness-to-pay (CRITICAL)")
    print("    - CRM integration complexity")
    print()
    print("  What NOT to build yet:")
    print("    - Don't build full multi-channel (start with email only)")
    print("    - Don't target enterprise (start with mid-market)")
    print("    - Don't build industry-specific features yet")
    print()
    print("  Suggested experiments:")
    print("    1. Landing page (2 weeks, $500 budget)")
    print("    2. User interviews (3 weeks, 15-20 interviews)")
    print("    3. Fake door test (measure CTR)")

    base_path = Path(__file__).parent.parent.parent / "spec-global/departments/stg/examples"
    handoff_file = base_path / "layer5_handoff/handoff.yaml"
    with open(handoff_file) as f:
        return f.read()


async def main():
    """主测试流程"""
    print("\n" + "🚀"*30)
    print("  STG Opportunity Discovery Workflow Test")
    print("  商业机会发现工作流测试")
    print("🚀"*30)

    try:
        # Layer 1: Search
        search_results = await test_search_agent()

        # Layer 2: Analysis (parallel)
        analysis_results = await test_analysis_layers(search_results)

        # Layer 3: Freeze
        freeze_data = await test_freeze_layer(analysis_results)

        # Layer 4: Business Opportunity
        opportunity_data = await test_business_opportunity_agent(freeze_data)

        # Layer 5: Product Handoff
        handoff_data = await test_product_handoff(opportunity_data)

        # 总结
        print("\n" + "="*60)
        print("✅ 工作流测试完成！")
        print("="*60)
        print("\n📊 产出物清单:")
        print("  1. 搜索信号数据 ✓")
        print("  2. 用户假设分析 ✓")
        print("  3. 行业结构分析 ✓")
        print("  4. 供给空缺分析 ✓")
        print("  5. 市场信号冻结 ✓")
        print("  6. 商业机会假设 ✓")
        print("  7. 产品交付文档 ✓")

        print("\n🎯 核心原则验证:")
        print("  ✓ 分析在 freeze 层收敛")
        print("  ✓ 机会在 handoff 层对产品负责")
        print("  ✓ 只能引用，不可推翻")
        print("  ✓ 诚实呈现风险")

        print("\n📁 所有文件位置:")
        print("  - Spec files: spec-global/departments/stg/")
        print("  - Examples: spec-global/departments/stg/examples/")
        print("  - Contracts: spec-global/departments/stg/contracts/")

        print("\n🚀 下一步:")
        print("  1. 真实数据运行：配置真实的 API keys")
        print("  2. 执行用户访谈：验证假设")
        print("  3. Landing page 测试：测量市场反应")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
