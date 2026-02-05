# Test Case Reviewer Agent

测试用例评审 Agent，用于评审手工产出的测试用例质量。

## 概述

Test Case Reviewer Agent 负责评审手工创建的测试用例，确保其满足以下质量标准：

- **完整性**：所有功能点和验收标准都有测试覆盖
- **准确性**：测试步骤清晰、预期结果具体可验证
- **覆盖度**：达到要求的测试覆盖率
- **契约符合性**：符合 test-case-contract 契约规范
- **可执行性**：测试用例可以被实际执行

## Agent 信息

| 属性 | 值 |
|------|-----|
| **Agent ID** | `agent.review.test_case_reviewer` |
| **部门** | QA |
| **版本** | v1.0.0 |
| **创建日期** | 2026-02-05 |

## 输入

Agent 需要以下输入文件：

1. **PRD 契约** (`frozen-detailed-prd-contract/v1/schema.json`)
   - 必须是已冻结状态 (`is_frozen: true`)
   - 包含功能需求和验收标准

2. **技术架构契约** (`frozen-technical-architecture-contract/v1/schema.json`)
   - 包含系统组件和接口定义

3. **测试用例契约** (`test-case-contract/v1/schema.json`)
   - 需要评审的测试用例文件

4. **UI 契约** (可选) (`ui-contract/v1/schema.json`)
   - 包含界面交互规范

## 输出

Agent 生成以下输出：

### 1. JSON 格式评审报告
符合 `test-case-review-contract/v1/schema.json` 契约，包含：

- **评审概要**：总体评分、评级、建议
- **维度评分**：五个评审维度的详细评分
- **问题清单**：所有发现的问题（按严重程度分类）
- **覆盖度分析**：功能覆盖、AC 覆盖、优先级覆盖分析
- **改进建议**：可操作的改进建议列表
- **契约符合性**：schema 验证结果
- **测试统计**：测试用例统计信息

### 2. Markdown 格式人类可读报告
包含评审概要、详细评分、问题清单、改进建议等内容。

## 评审维度

| 维度 | 权重 | 说明 |
|------|------|------|
| **完整性** | 25% | 检查测试用例是否覆盖所有功能和验收标准 |
| **准确性** | 25% | 检查测试步骤和预期结果的准确性 |
| **覆盖度** | 25% | 评估测试覆盖率是否达标 |
| **契约符合性** | 15% | 验证是否符合 test-case-contract 规范 |
| **可执行性** | 10% | 评估测试用例的可执行性 |

## 评分标准

| 总分 | 评级 | 说明 |
|------|------|------|
| >= 90 | EXCELLENT | 优秀，通过评审 |
| >= 70 | GOOD | 良好，有轻微问题，建议改进 |
| >= 50 | FAIR | 一般，有明显问题，需要修订 |
| < 50 | POOR | 差，有严重问题，必须重新编写 |

## 问题严重程度

| 级别 | 说明 | 阻碍通过 |
|------|------|----------|
| **blocker** | 阻塞性问题，必须修复 | 是 |
| **major** | 重大问题，应该修复 | 通常 |
| **minor** | 轻微问题，建议修复 | 否 |
| **nit** | 细节问题，可选修复 | 否 |

## 使用方法

### 通过 LEE 框架调用

```bash
# 调用 Agent 进行评审
lee invoke agent.review.test_case_reviewer \
  --input.prd=path/to/prd.json \
  --input.architecture=path/to/architecture.json \
  --input.test_cases=path/to/test_cases.json \
  --input.ui=path/to/ui.json \
  --output.path=output/review
```

### 输入文件示例

```json
// test_cases.json
{
  "contract_type": "test-case",
  "contract_version": "1.0.0",
  "metadata": {
    "contract_id": "TC-20260205-001",
    "product_name": "User Authentication",
    "created_date": "2026-02-05T10:00:00Z",
    "status": "READY_FOR_REVIEW",
    "created_by": "test-engineer"
  },
  "test_plan": {
    "test_suites": [
      {
        "suite_id": "TS-001",
        "name": "Login Tests",
        "type": "e2e",
        "priority": "P0",
        "test_cases": [
          {
            "test_id": "TC-0001",
            "title": "Successful Login",
            "priority": "P0",
            "scenario": "User logs in with valid credentials",
            "steps": [
              {
                "step_number": 1,
                "action": "Navigate to login page",
                "expected_result": "Login page is displayed"
              }
            ],
            "expected_result": "User is redirected to dashboard"
          }
        ]
      }
    ]
  }
}
```

### 输出示例

```json
{
  "contract_type": "test-case-review",
  "contract_version": "1.0.0",
  "metadata": {
    "contract_id": "TCR-20260205-001",
    "product_name": "User Authentication",
    "review_date": "2026-02-05T11:00:00Z",
    "reviewer": "agent.review.test_case_reviewer",
    "test_case_contract_id": "TC-20260205-001"
  },
  "review_summary": {
    "total_score": 75,
    "rating": "GOOD",
    "total_test_cases": 15,
    "total_findings": 5,
    "recommendation": "APPROVED_WITH_SUGGESTIONS",
    "summary_text": "测试用例整体质量良好，覆盖了主要功能场景。建议补充边界值测试和异常场景。"
  },
  "dimension_scores": [
    {
      "dimension": "completeness",
      "score": 80,
      "weight": 0.25,
      "weighted_score": 20,
      "status": "PASS"
    },
    {
      "dimension": "accuracy",
      "score": 85,
      "weight": 0.25,
      "weighted_score": 21.25,
      "status": "PASS"
    },
    {
      "dimension": "coverage",
      "score": 70,
      "weight": 0.25,
      "weighted_score": 17.5,
      "status": "WARNING"
    },
    {
      "dimension": "contract_compliance",
      "score": 100,
      "weight": 0.15,
      "weighted_score": 15,
      "status": "PASS"
    },
    {
      "dimension": "executability",
      "score": 90,
      "weight": 0.10,
      "weighted_score": 9,
      "status": "PASS"
    }
  ],
  "findings": [
    {
      "id": "F-0001",
      "severity": "major",
      "category": "coverage",
      "title": "Missing boundary value test for password field",
      "description": "Password field lacks boundary value testing (min/max length)",
      "location": {
        "suite_id": "TS-001"
      },
      "impact": "May miss edge cases related to password length validation",
      "suggestion": "Add test cases for password with minimum and maximum allowed length"
    }
  ],
  "coverage_analysis": {
    "feature_coverage": {
      "total_features": 5,
      "covered_features": 5,
      "coverage_percentage": 100
    },
    "ac_coverage": {
      "total_acceptance_criteria": 12,
      "covered_ac": 11,
      "coverage_percentage": 91.67,
      "uncovered_ac": [
        {
          "ac_id": "AC-005",
          "ac_text": "Password must be at least 8 characters",
          "feature_id": "F-001"
        }
      ]
    }
  },
  "improvement_suggestions": [
    {
      "id": "S-0001",
      "priority": "high",
      "category": "add_test_cases",
      "suggestion": "Add boundary value tests for password field (7, 8, 128, 129 characters)",
      "rationale": "Ensures password length validation is properly tested"
    }
  ]
}
```

## 工作流程

1. **输入验证**：验证所有输入文件完整且有效
2. **需求提取**：从 PRD 和架构文档中提取功能需求
3. **契约符合性检查**：验证测试用例符合 schema 规范
4. **完整性评审**：检查测试覆盖是否完整
5. **覆盖度分析**：计算并分析测试覆盖率
6. **准确性评审**：检查测试步骤和预期结果
7. **可执行性评估**：评估测试用例的可执行性
8. **优先级评估**：检查测试优先级分配
9. **评分计算**：计算各维度和总体评分
10. **报告生成**：生成评审报告

## 质量门槛

### 必须满足 (Must Have)
- 所有 P0 功能点都有测试覆盖
- 所有验收标准都有对应测试用例
- 测试步骤清晰明确、可执行
- 预期结果具体可验证
- 测试数据定义完整
- 符合 test-case-contract 契约规范
- 包含正常路径和异常路径测试

### 建议满足 (Should Have)
- 边界值测试覆盖
- 性能和安全测试场景考虑
- 自动化可行性评估
- 测试优先级标记合理
- 前置条件和后置条件明确

## 拒绝条件

Agent 在以下情况下会拒绝执行评审：

- 测试用例文件未提供
- PRD 未冻结 (`is_frozen != true`)
- 缺少必需的输入契约

## 版本历史

### v1.0.0 (2026-02-05)
- 初始版本
- 五维评审框架
- 契约符合性验证
- 覆盖度分析和缺口识别
- 可操作的改进建议

## 相关契约

- 输入契约：
  - `frozen-detailed-prd-contract/v1/schema.json`
  - `frozen-technical-architecture-contract/v1/schema.json`
  - `test-case-contract/v1/schema.json`
  - `ui-contract/v1/schema.json` (可选)

- 输出契约：
  - `test-case-review-contract/v1/schema.json`

## 相关 Agent

- **Test Case Creator** (`agent.testing.test_case_creator`): 创建测试用例
- **Test Report Generator** (`agent.qa.test_report_generator`): 生成测试报告
- **Bug Manager** (`agent.qa.bug_manager`): 管理缺陷

## 维护者

- Agent Spec Maintainer
- QA Team

## 许可

本 Agent 规范遵循 LEE 框架的许可协议。
