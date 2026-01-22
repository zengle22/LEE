#!/usr/bin/env python3
"""
部门 README 文档生成器

为 LEE 框架的每个部门自动生成 README.md 文档。
"""

import os
from pathlib import Path
from datetime import datetime

# 部门配置
DEPARTMENTS = {
    "stg": {
        "name": "战略部门",
        "name_en": "Strategy",
        "description": "负责商业机会分析、市场研究、供应链分析、行业洞察和趋势研究",
        "responsibilities": [
            "市场机会识别与评估",
            "商业洞察生成",
            "供应链分析",
            "行业趋势研究",
            "竞争分析",
        ],
        "workflows": [
            ("market_research.yaml", "市场研究工作流", "市场研究需求", "市场研究报告"),
            ("opportunity_analysis.yaml", "机会分析工作流", "业务机会", "机会评估报告"),
            ("supply_analysis.yaml", "供应链分析工作流", "供应链数据", "供应链分析报告"),
        ],
        "gates": [
            ("business_value_check.yaml", "商业价值检查", "提交 PRD 前", "商业价值评分 >= 80"),
            ("market_fit_gate.yaml", "市场契合度检查", "产品发布前", "市场需求验证通过"),
        ],
        "agents": [
            ("business-opportunity-analyzer.yaml", "商业机会分析", "识别和分析商业机会"),
            ("supply-analyzer.yaml", "供应链分析", "分析供应链结构和成本"),
            ("google-keyword-searcher.yaml", "关键词搜索", "搜索市场关键词数据"),
            ("google-trend-analyzer.yaml", "趋势分析", "分析市场趋势"),
            ("industry-structure-analyzer.yaml", "行业结构分析", "分析行业结构和竞争格局"),
        ],
        "skills": [
            ("market-analysis.yaml", "市场分析技能"),
            ("competitive-intelligence.yaml", "竞争情报技能"),
        ],
        "contracts": [
            ("business-opportunity-contract.yaml", "商业机会契约"),
            ("supply-analysis-contract.yaml", "供应链分析契约"),
            ("market-insight-contract.yaml", "市场洞察契约"),
        ],
        "collaborations": [
            ("prd", "stg-prd 业务需求契约", "市场到产品 E2E 工作流"),
        ],
    },
    "prd": {
        "name": "产品部门",
        "name_en": "Product",
        "description": "负责产品需求文档（PRD）编写、需求评审和产品目标定义",
        "responsibilities": [
            "需求收集与整理",
            "PRD 编写和维护",
            "需求评审",
            "产品目标定义",
            "用户故事管理",
        ],
        "workflows": [
            ("requirement_intake.yaml", "需求录入工作流", "用户需求", "需求文档"),
            ("prd_writing.yaml", "PRD 编写工作流", "需求文档", "PRD"),
            ("requirement_review.yaml", "需求评审工作流", "PRD 草稿", "评审报告"),
        ],
        "gates": [
            ("prd_quality_gate.yaml", "PRD 质量门禁", "提交开发前", "PRD 质量评分 >= 80"),
            ("requirement_completeness_gate.yaml", "需求完整性门禁", "需求评审前", "需求完整性 100%"),
        ],
        "agents": [
            ("prd-writer.yaml", "PRD 编写", "编写产品需求文档"),
            ("requirement-reviewer.yaml", "需求评审", "评审需求文档"),
            ("product-goal-analyzer.yaml", "产品目标分析", "分析并定义产品目标"),
        ],
        "skills": [
            ("product-planning.yaml", "产品规划技能"),
            ("requirement-analysis.yaml", "需求分析技能"),
        ],
        "contracts": [
            ("prd_contract.yaml", "PRD 契约"),
            ("user-story-contract.yaml", "用户故事契约"),
            ("product-goal-contract.yaml", "产品目标契约"),
        ],
        "collaborations": [
            ("stg", "stg-prd 业务需求契约", "市场到产品 E2E 工作流"),
            ("ui", "prd-ui 设计需求契约", "产品到设计 E2E 工作流"),
            ("dev", "prd-dev 需求包契约", "产品到开发 E2E 工作流"),
        ],
    },
    "ui": {
        "name": "UI 设计部门",
        "name_en": "UI Design",
        "description": "负责 UI 设计、设计系统维护和设计规范管理",
        "responsibilities": [
            "UI 设计",
            "设计系统维护",
            "设计规范制定",
            "原型设计",
            "视觉设计",
        ],
        "workflows": [
            ("ui_design.yaml", "UI 设计工作流", "PRD", "UI 设计稿"),
            ("design_review.yaml", "设计评审工作流", "UI 设计稿", "评审报告"),
        ],
        "gates": [
            ("design_quality_gate.yaml", "设计质量门禁", "提交开发前", "设计质量评分 >= 80"),
            ("design_system_compliance_gate.yaml", "设计系统合规门禁", "设计评审前", "符合设计系统规范"),
        ],
        "agents": [
            ("ui-designer.yaml", "UI 设计师", "设计用户界面"),
            ("icon-generator.yaml", "图标生成", "生成应用图标"),
            ("ui-contract-generator.yaml", "UI 契约生成", "生成 UI 设计契约"),
            ("ui-contract-validator.yaml", "UI 契约验证", "验证 UI 设计契约"),
        ],
        "skills": [
            ("design-system.yaml", "设计系统技能"),
            ("visual-design.yaml", "视觉设计技能"),
        ],
        "contracts": [
            ("ui-design-contract.yaml", "UI 设计契约"),
        ],
        "collaborations": [
            ("prd", "prd-ui 设计需求契约", "产品到设计 E2E 工作流"),
            ("dev", "ui-dev UI 规范契约", "设计到开发 E2E 工作流"),
        ],
    },
    "dev": {
        "name": "开发部门",
        "name_en": "Development",
        "description": "负责架构设计、代码实现、代码审查和技术文档编写",
        "responsibilities": [
            "架构设计",
            "代码实现",
            "代码审查",
            "技术文档编写",
            "单元测试",
        ],
        "workflows": [
            ("architecture_design.yaml", "架构设计工作流", "PRD", "架构文档"),
            ("code_implementation.yaml", "代码实现工作流", "架构文档", "源代码"),
            ("code_review.yaml", "代码审查工作流", "代码 PR", "审查报告"),
            ("self_testing.yaml", "自测工作流", "代码", "测试结果"),
        ],
        "gates": [
            ("code_quality_gate.yaml", "代码质量门禁", "提交测试前", "代码质量评分 >= 80"),
            ("test_coverage_gate.yaml", "测试覆盖率门禁", "合并到主分支前", "测试覆盖率 >= 80%"),
            ("security_review_gate.yaml", "安全审查门禁", "发布前", "安全审查通过"),
        ],
        "agents": [
            ("tech-architect.yaml", "技术架构师", "设计系统架构"),
            ("backend-engineer.yaml", "后端工程师", "实现后端逻辑"),
            ("frontend-engineer.yaml", "前端工程师", "实现前端界面"),
            ("code-reviewer.yaml", "代码审查员", "审查代码质量"),
        ],
        "skills": [
            ("api-design.yaml", "API 设计技能"),
            ("coding-standards.yaml", "编码规范技能"),
        ],
        "contracts": [
            ("api_spec_contract.yaml", "API 规范契约"),
            ("design_doc_contract.yaml", "设计文档契约"),
        ],
        "collaborations": [
            ("prd", "prd-dev 需求包契约", "产品到开发 E2E 工作流"),
            ("ui", "ui-dev UI 规范契约", "设计到开发 E2E 工作流"),
            ("qa", "dev-qa 测试输入契约", "开发到测试 E2E 工作流"),
        ],
    },
    "qa": {
        "name": "测试部门",
        "name_en": "QA",
        "description": "负责测试用例设计、测试执行、Bug 分析和测试报告编写",
        "responsibilities": [
            "测试用例设计",
            "测试执行",
            "Bug 分析和分类",
            "测试报告编写",
            "自动化测试",
        ],
        "workflows": [
            ("test_case_design.yaml", "测试用例设计工作流", "需求/设计", "测试用例"),
            ("test_execution.yaml", "测试执行工作流", "测试用例", "测试结果"),
            ("bug_triage.yaml", "Bug 分析工作流", "Bug 报告", "Bug 分类"),
            ("test_report.yaml", "测试报告工作流", "测试数据", "测试报告"),
        ],
        "gates": [
            ("test_pass_rate_gate.yaml", "测试通过率门禁", "发布前", "测试通过率 >= 95%"),
            ("critical_bugs_gate.yaml", "关键 Bug 门禁", "发布前", "无 P0/P1 Bug"),
        ],
        "agents": [
            ("test-case-creator.yaml", "测试用例设计师", "设计测试用例"),
            ("test-executor.yaml", "测试执行员", "执行测试"),
            ("bug-analyzer.yaml", "Bug 分析师", "分析和分类 Bug"),
        ],
        "skills": [
            ("test-strategy.yaml", "测试策略技能"),
            ("automation.yaml", "自动化测试技能"),
        ],
        "contracts": [
            ("test_plan_contract.yaml", "测试计划契约"),
            ("bug_report_contract.yaml", "Bug 报告契约"),
            ("test_report_contract.yaml", "测试报告契约"),
        ],
        "collaborations": [
            ("dev", "dev-qa 测试输入契约", "开发到测试 E2E 工作流"),
            ("ops", "qa-ops 发布就绪契约", "测试到运维 E2E 工作流"),
        ],
    },
    "ops": {
        "name": "运维部门",
        "name_en": "Operations",
        "description": "负责部署、监控、故障响应和基础设施管理",
        "responsibilities": [
            "系统部署",
            "监控配置",
            "故障响应",
            "基础设施管理",
            "性能优化",
        ],
        "workflows": [
            ("deployment.yaml", "部署工作流", "发布包", "部署完成"),
            ("monitoring_setup.yaml", "监控配置工作流", "系统", "监控系统"),
            ("incident_response.yaml", "故障响应工作流", "故障报告", "故障解决"),
        ],
        "gates": [
            ("deployment_success_gate.yaml", "部署成功门禁", "切换流量前", "部署成功且健康检查通过"),
            ("uptime_sla_gate.yaml", "可用性 SLA 门禁", "发布后", "SLA 达标"),
        ],
        "agents": [
            ("devops-engineer.yaml", "DevOps 工程师", "负责部署和运维"),
            ("sre.yaml", "SRE", "负责系统可靠性"),
        ],
        "skills": [
            ("infrastructure.yaml", "基础设施技能"),
            ("monitoring.yaml", "监控技能"),
        ],
        "contracts": [
            ("deployment_plan_contract.yaml", "部署计划契约"),
        ],
        "collaborations": [
            ("qa", "qa-ops 发布就绪契约", "测试到运维 E2E 工作流"),
        ],
    },
    "office": {
        "name": "办公室/行政",
        "name_en": "Office",
        "description": "暂时存放不属于其他部门的 spec，未来可以独立成新的部门",
        "responsibilities": [
            "行政事务管理",
            "通用流程管理",
            "待分类的 spec 管理",
        ],
        "workflows": [],
        "gates": [],
        "agents": [],
        "skills": [],
        "contracts": [],
        "collaborations": [],
    },
}

def create_readme(dept_id: str, dept_config: dict, output_dir: Path):
    """为部门创建 README.md"""

    readme_path = output_dir / dept_id / "README.md"

    content = f"""# {dept_config['name']} ({dept_id})

> {dept_config['name_en']} Department

## 部门职责

{dept_config['description']}

### 主要职责

"""

    for resp in dept_config['responsibilities']:
        content += f"- {resp}\n"

    content += """
## 目录结构

```
{dept_id}/
├── workflows/      # 部门工作流
├── gates/          # 部门门禁
├── agents/         # 部门专属 agent
├── skills/         # 部门技能
└── contracts/      # 部门交付物契约
```

## 工作流 (workflows)

| 工作流 | 说明 | 输入 | 输出 |
|--------|------|------|------|
"""

    for workflow in dept_config['workflows']:
        content += f"| {workflow[0]} | {workflow[1]} | {workflow[2]} | {workflow[3]} |\n"

    if not dept_config['workflows']:
        content += "| _（暂无）_ | - | - | - |\n"

    content += """
## 门禁 (gates)

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|
"""

    for gate in dept_config['gates']:
        content += f"| {gate[0]} | {gate[1]} | {gate[2]} |\n"

    if not dept_config['gates']:
        content += "| _（暂无）_ | - | - |\n"

    content += """
## Agent 列表

| Agent | 职责 | 说明 |
|-------|------|------|
"""

    for agent in dept_config['agents']:
        content += f"| {agent[0]} | {agent[1]} | {agent[2]} |\n"

    if not dept_config['agents']:
        content += "| _（暂无）_ | - | - |\n"

    content += """
## 技能 (skills)

| 技能 | 说明 |
|------|------|
"""

    for skill in dept_config['skills']:
        content += f"| {skill[0]} | {skill[1]} |\n"

    if not dept_config['skills']:
        content += "| _（暂无）_ | - |\n"

    content += """
## 契约 (contracts)

| 契约 | 说明 |
|------|------|
"""

    for contract in dept_config['contracts']:
        content += f"| {contract[0]} | {contract[1]} |\n"

    if not dept_config['contracts']:
        content += "| _（暂无）_ | - |\n"

    content += """
## 跨部门协作

### 协作关系

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
"""

    for collab in dept_config['collaborations']:
        content += f"| {collab[0]} | {collab[1]} | {collab[2]} |\n"

    if not dept_config['collaborations']:
        content += "| _（暂无）_ | - | - |\n"

    content += f"""
---

**最后更新**：{datetime.now().strftime('%Y-%m-%d')}

**维护者**：LEE 框架团队
"""

    # 写入文件
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text(content, encoding='utf-8')

    print(f"✓ 创建 {dept_id}/README.md")

def main():
    """主函数"""

    print("=" * 60)
    print("部门 README 文档生成器")
    print("=" * 60)
    print()

    output_dir = Path("spec-global/departments")

    if not output_dir.exists():
        print("错误：spec-global/departments 目录不存在")
        print("请先运行迁移脚本")
        return

    print(f"输出目录：{output_dir.absolute()}")
    print()

    for dept_id, dept_config in DEPARTMENTS.items():
        create_readme(dept_id, dept_config, output_dir)

    print()
    print("=" * 60)
    print("部门 README 创建完成！")
    print("=" * 60)
    print()
    print("已为以下部门创建 README.md：")
    for dept_id in DEPARTMENTS.keys():
        readme_path = output_dir / dept_id / "README.md"
        if readme_path.exists():
            print(f"  ✓ {dept_id}/README.md")
    print()
    print("查看部门文档：")
    print(f"  cat spec-global/departments/{{stg,prd,ui,dev,qa,ops,office}}/README.md")

if __name__ == "__main__":
    main()
