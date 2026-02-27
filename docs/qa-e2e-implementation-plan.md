# LEE QA E2E 测试执行闭环实现方案 v2.0（最终版）

## 文档信息

| 项目 | 内容 |
|------|------|
| **版本** | v3.0（含单元测试/集成/评审） |
| **日期** | 2026-02-27 |
| **状态** | ✅ 已完成 (2026-02-27) |
| **实际工期** | ~2 天（AI 辅助开发） |
| **完成总结** | 见 [PROJECT_SUMMARY.md](./qa/PROJECT_SUMMARY.md) |

---

## 目录

- [一、方案概述](#一方案概述)
- [二、整体架构](#二整体架构)
- [三、核心模块设计](#三核心模块设计)
- [四、LLM 代码生成质量保证](#四llm-代码生成质量保证)
- [五、错误分类与诊断](#五错误分类与诊断)
- [六、实施计划](#六实施计划)
  - [6.1 时间估算](#61-时间估算)
  - [6.2 实施顺序](#62-实施顺序)
  - [6.3 里程碑](#63-里程碑)
  - [6.4 单元测试策略](#64-单元测试策略)
  - [6.5 系统集成测试](#65-系统集成测试)
  - [6.6 代码评审流程](#66-代码评审流程)
- [七、风险评估](#七风险评估)

---

## 一、方案概述

### 1.1 目标

实现 QA 测试流程的**完整执行闭环**，使 L3 工作流能够：
1. 从 YAML 测试用例生成可执行的 Python Playwright 代码
2. 本地执行测试（无需强制 Docker）
3. 准确区分**测试代码问题** vs **被测系统问题**
4. 自动修复测试代码问题，或报告系统 Bug

### 1.2 核心设计决策

| 决策 | 理由 |
|------|------|
| **Python Playwright** | 直接 API 调用，无需 subprocess → Node.js |
| **本地执行优先** | 开发调试友好，Docker 作为可选项 |
| **Agent 驱动生成** | 用 LLM 理解自然语言用例，生成代码 |
| **多层质量保证** | 结构 → 语法 → 语义 → 运行时验证 |
| **错误自动分类** | 代码问题 vs 系统问题，减少 False Fail |

### 1.3 与现有系统的集成

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LEE QA 现有系统                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                               │
│  spec-global/departments/qa/                                                  │
│  ├── agents/                                                                │
│  │   ├── case-generator/v1/agent.yaml     ← Step 1: 生成用例                 │
│  │   ├── script-translator/v1/agent.yaml  ← Step 2: 生成脚本（本方案实现）   │
│  │   ├── result-judge/v1/agent.yaml       ← Step 5: 判定结果（扩展）         │
│  │   └── bug-drafter/v1/agent.yaml         ← Step 7: Bug 起草                 │
│  ├── contracts/                                                             │
│  │   ├── test-case/v1/schema.yaml          ← 用例契约                     │
│  │   └── test-result/v1/schema.yaml         ← 结果契约                     │
│  └── workflows/                                                             │
│      └── templates/test-set-l3-template.yaml  ← L3 工作流模板                │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 本方案实现
┌─────────────────────────────────────────────────────────────────────────────┐
│                           新增 Python 实现层                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                               │
│  lee/qa/                                                                      │
│  ├── generator/          ← 代码生成器（Agent 驱动）                            │
│  │   ├── __init__.py                                                          │
│  │   ├── base.py              ← 生成器基类                                    │
│  │   ├── playwright_gen.py   ← Playwright 生成器                              │
│  │   └── templates/           ← Jinja2 模板                                   │
│  ├── runner/              ← 测试执行器                                         │
│  │   ├── __init__.py                                                          │
│  │   ├── base.py              ← 执行器基类                                    │
│  │   ├── local.py             ← 本地执行器（Python Playwright API）          │
│  │   └── docker.py            ← Docker 执行器（可选）                          │
│  ├── validator/            ← 代码质量验证                                       │
│  │   ├── __init__.py                                                          │
│  │   ├── schema_validator.py   ← 结构验证（Layer 1）                        │
│  │   ├── syntax_validator.py   ← 语法验证（Layer 2）                        │
│  │   ├── selector_validator.py ← 选择器验证（Layer 3）                       │
│  │   └── timeout_validator.py  ← 超时验证（Layer 3）                         │
│  ├── classifier/           ← 错误分类器                                         │
│  │   ├── __init__.py                                                          │
│  │   ├── error_classifier.py  ← 错误分类（代码 vs 系统）                      │
│  │   └── context_collector.py  ← 上下文收集                                   │
│  └── fixer/               ← 自动修复                                             │
│      ├── __init__.py                                                          │
│      └── auto_fixer.py        ← 代码问题自动修复                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、整体架构

### 2.1 执行流程图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            L3 Test Set Execution                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                                   │
│  Input: test_set.yaml (Test Set 定义)                                         │
│         │                                                                      │
│         ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  Step 1: Case Generation                                           │     │
│  │  ─────────────────────────────────────────────────────────────────  │     │
│  │  Agent: agent.qa.case_generator                                     │     │
│  │  Input: test_set.strategy                                          │     │
│  │  Output: cases.yaml (动态用例)                                       │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│         │                                                                      │
│         ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  Step 2: Script Translation (代码生成)                              │     │
│  │  ─────────────────────────────────────────────────────────────────  │     │
│  │  Agent: agent.qa.script_translator                                  │     │
│  │  │                                                                      │     │
│  │  ┌─────────────────────────────────────────────────────────────┐     │     │
│  │  │  CodeGenerator.generate_with_validation()                      │     │     │
│  │  │  ├─ LLM 生成 Python Playwright 代码                            │     │     │
│  │  │  ├─ Layer 1: Schema 验证（结构检查）                            │     │     │
│  │  │  ├─ Layer 2: Syntax 验证（AST 解析）                            │     │     │
│  │  │  ├─ Layer 3: Static Analysis（选择器、超时）                     │     │     │
│  │  │  └─ 失败 → 反馈 LLM → 重新生成（最多3次）                         │     │     │
│  │  └─────────────────────────────────────────────────────────────┘     │     │
│  │  │                                                                      │     │
│  │  Output: scripts/                                                      │     │
│  │          ├── test_*.py                                               │     │
│  │          ├── conftest.py                                             │     │
│  │          └── validation.json                                        │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│         │                                                                      │
│         ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  Step 3: Script Execution                                           │     │
│  │  ─────────────────────────────────────────────────────────────────  │     │
│  │  Skill: skill.runner.test_e2e                                       │     │
│  │  │                                                                      │     │
│  │  ┌─────────────────────────────────────────────────────────────┐     │     │
│  │  │  LocalRunner.execute() (默认)                                 │     │     │
│  │  │  ├─ exec(test_script)                                          │     │     │
│  │  │  ├─ 收集: stdout, stderr, exit_code                             │     │     │
│  │  │  ├─ 证据: screenshots, traces, logs                              │     │     │
│  │  │  └─ Output: runner-output.json                                 │     │     │
│  │  └─────────────────────────────────────────────────────────────┘     │     │
│  │  │                                                                      │     │
│  │  └─ 或 DockerRunner.execute() (可选)                                │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│         │                                                                      │
│         ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  Step 4: Behavior Compliance Check                                  │     │
│  │  ─────────────────────────────────────────────────────────────────  │     │
│  │  Skill: skill.qa.behavior_compliance_checker                         │     │
│  │  ├─ 检查: EXECUTOR 是否伪造执行                                       │     │
│  │  ├─ 检查: 证据是否完整                                                 │     │
│  │  └─ Output: compliance.json                                          │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│         │                                                                      │
│         ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  Step 5: Result Judgment (结果判定 + 错误分类)                        │     │
│  │  ─────────────────────────────────────────────────────────────────  │     │
│  │  Agent: agent.qa.result_judge                                       │     │
│  │  │                                                                      │     │
│  │  ┌─────────────────────────────────────────────────────────────┐     │     │
│  │  │  ErrorClassifier.classify(error, context)                      │     │     │
│  │  │  ├─ 代码问题 (False Fail)                                      │     │     │
│  │  │  │   → 记录但不上报 Bug                                          │     │     │
│  │  │  │   → 自动修复 → 重新执行                                       │     │     │
│  │  │  ├─ 系统问题 (True Fail)                                        │     │     │
│  │  │  │   → 准备 Bug 报告                                            │     │     │
│  │  │  └─ 不确定                                                       │     │     │
│  │  │      → 收集更多上下文 → 人工审查                                 │     │     │
│  │  └─────────────────────────────────────────────────────────────┘     │     │
│  │  │                                                                      │     │
│  │  Output: results.yaml                                                │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│         │                                                                      │
│         ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  Step 6: TSE Assembly                                                │     │
│  │  Agent: agent.qa.tse_assembler                                       │     │
│  │  Output: tse.yaml                                                      │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│         │                                                                      │
│         ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  Step 7: Bug Drafting (条件执行)                                     │     │
│  │  Agent: agent.qa.bug_drafter                                         │     │
│  │  Condition: fail_count > 0 AND 有 True Fail                           │     │
│  │  Output: bug_drafts/*.yaml                                            │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                                   │
│  Output: test_set_execution/                                            │
│          ├── scripts/                                                   │
│          ├── validation.json                                            │
│          ├── runner-output.json                                         │
│          ├── compliance.json                                            │
│          ├── results.yaml                                               │
│          ├── tse.yaml                                                   │
│          └── evidence/                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构（最终版）

```
lee/
├── docs/
│   └── qa-e2e-implementation-plan.md    # 本文档
│
├── qa/                                # 新增目录
│   ├── __init__.py
│   │
│   ├── generator/                       # 代码生成器
│   │   ├── __init__.py
│   │   ├── base.py                    # 生成器基类
│   │   ├── playwright_gen.py         # Playwright 生成器
│   │   ├── cypress_gen.py            # Cypress 生成器（预留）
│   │   └── templates/
│   │       ├── base.py.j2             # 基础模板
│   │       ├── conftest.py.j2         # pytest 配置
│   │       └── test_case.py.j2        # 测试用例模板
│   │
│   ├── runner/                          # 测试执行器
│   │   ├── __init__.py
│   │   ├── base.py                    # 执行器基类
│   │   ├── local.py                   # 本地执行器
│   │   ├── docker.py                  # Docker 执行器（可选）
│   │   └── context.py                 # 执行上下文
│   │
│   ├── validator/                       # 代码质量验证
│   │   ├── __init__.py
│   │   ├── base.py                    # 验证器基类
│   │   ├── schema_validator.py        # 结构验证（L1）
│   │   ├── syntax_validator.py        # 语法验证（L2）
│   │   ├── selector_validator.py      # 选择器验证（L3）
│   │   ├── timeout_validator.py       # 超时验证（L3）
│   │   └── result.py                  # 验证结果
│   │
│   ├── classifier/                      # 错误分类器
│   │   ├── __init__.py
│   │   ├── error_classifier.py        # 主分类器
│   │   ├── patterns.py                # 错误模式匹配
│   │   └── context_collector.py       # 上下文收集
│   │
│   ├── fixer/                           # 自动修复
│   │   ├── __init__.py
│   │   ├── auto_fixer.py              # 自动修复器
│   │   └── strategies/                # 修复策略
│   │       ├── selector_fix.py        # 选择器修复
│   │       └── timeout_fix.py          # 超时修复
│   │
│   └── utils/                           # 工具函数
│       ├── __init__.py
│       ├── llm.py                      # LLM 调用封装
│       └── logger.py                   # 日志工具
│
├── src/lee/cli/commands/
│   ├── qa/
│   │   ├── test_plan.py               # 已存在
│   │   ├── test_run.py                # 已存在
│   │   ├── test_set.py                # 已存在
│   │   └── test_runner.py             # 已存在，需扩展
│   │
│   └── test_runner.py                 # 已存在，需验证
│
└── tests/                              # 单元测试
    └── qa/
        ├── test_generator.py
        ├── test_runner.py
        ├── test_validator.py
        └── test_classifier.py
```

---

## 三、核心模块设计

### 3.1 代码生成器（Generator）

#### 3.1.1 基类设计

```python
# qa/generator/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from qa.validator.result import ValidationResult

@dataclass
class GenerationRequest:
    """生成请求"""
    test_cases: List[Dict]
    base_url: str
    framework: str = "playwright"
    options: Dict[str, Any] = None

@dataclass
class GenerationResult:
    """生成结果"""
    code: str
    files: Dict[str, str]              # 文件名 → 内容
    validation: ValidationResult
    retries: int                      # 重试次数

class BaseGenerator(ABC):
    """代码生成器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """生成器名称"""
        pass

    @property
    @abstractmethod
    def framework(self) -> str:
        """支持的框架"""
        pass

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """生成代码（带验证和重试）"""
        pass

    def _validate_and_retry(
        self,
        request: GenerationRequest,
        max_retries: int = 3
    ) -> GenerationResult:
        """生成并验证，失败则重试"""
        from qa.validator.schema_validator import SchemaValidator
        from qa.validator.syntax_validator import SyntaxValidator

        for attempt in range(max_retries):
            # 1. 生成代码
            code = self._llm_generate(request)

            # 2. 结构验证
            schema_result = SchemaValidator.validate(code)
            if not schema_result.is_valid:
                code = self._retry_with_schema_feedback(
                    request, code, schema_result.errors
                )
                continue

            # 3. 语法验证
            syntax_result = SyntaxValidator.validate(code)
            if not syntax_result.is_valid:
                code = self._retry_with_syntax_feedback(
                    request, code, syntax_result.errors
                )
                continue

            # 4. 静态分析
            static_result = self._static_analysis(code)
            if static_result.warnings:
                # 警告不阻止执行，但记录下来
                pass

            return GenerationResult(
                code=code,
                files=self._split_into_files(code),
                validation=ValidationResult.merge(
                    schema_result, syntax_result, static_result
                ),
                retries=attempt,
            )

        # 重试次数用尽
        raise CodeGenerationError(
            f"Failed to generate valid code after {max_retries} attempts",
            last_validation=schema_result,
        )

    @abstractmethod
    def _llm_generate(self, request: GenerationRequest) -> str:
        """调用 LLM 生成代码"""
        pass

    def _retry_with_schema_feedback(
        self,
        request: GenerationRequest,
        code: str,
        errors: List[Dict]
    ) -> str:
        """根据结构验证反馈重新生成"""
        feedback_prompt = self._build_feedback_prompt(code, errors)
        return self._llm_generate_with_feedback(request, feedback_prompt)

    def _split_into_files(self, code: str) -> Dict[str, str]:
        """将代码拆分为多个文件"""
        # 解析 Python AST，按类/函数拆分
        # 这里简化处理，实际需要更复杂的逻辑
        return {
            "test_main.py": code,
        }
```

#### 3.1.2 Playwright 生成器

```python
# qa/generator/playwright_gen.py

from jinja2 import Template
from qa.generator.base import BaseGenerator, GenerationRequest, GenerationResult
from qa.utils.llm import LLMClient

class PlaywrightGenerator(BaseGenerator):
    """Playwright 代码生成器"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm or LLMClient()
        self._load_templates()

    @property
    def name(self) -> str:
        return "playwright"

    @property
    def framework(self) -> str:
        return "playwright"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """生成 Playwright 测试代码"""
        return self._validate_and_retry(request)

    def _llm_generate(self, request: GenerationRequest) -> str:
        """调用 LLM 生成代码"""

        # 1. 构建系统提示
        system_prompt = self._get_system_prompt()

        # 2. 构建用户提示
        user_prompt = self._build_user_prompt(request)

        # 3. 调用 LLM
        response = self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,  # 降低随机性，提高稳定性
        )

        return self._extract_code(response)

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个 Playwright 测试代码生成专家。

# 代码规范

1. 使用 playwright.sync_api
2. 使用 pytest 框架
3. 每个测试用例一个独立的 test 函数
4. 使用 data-testid 选择器（优先级最高）
5. 包含适当的错误处理
6. 使用 page.expect_*() 进行断言
7. 添加清晰的 docstring

# 代码结构

```python
import pytest
from playwright.sync_api import sync_playwright, expect

@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            base_url=os.getenv("BASE_URL", "http://localhost:3000"),
        )
        page = context.new_page()
        yield page
        browser.close()

def test_case_name(page):
    \"\"\"
    用例标题：描述测试目标

    步骤：
    1. 步骤描述
    2. 步骤描述

    预期：预期结果
    \"\"\"
    # 测试代码
```

# 选择器优先级

1. data-testid="xxx" - 最稳定，推荐
2. id="xxx" - 稳定
3. [role="button"] - ARIA role，较稳定
4. .class-name - 不推荐，可能变化
5. text="xxx" - 不推荐，国际化问题

# 超时配置

- 默认超时：30000ms
- page.goto() 超时：60000ms（等待网络）
- page.click() 超时：默认（auto-wait）
- 避免使用 page.wait_for_timeout()

# 断言模式

- expect(page.locator()).to_be_visible()
- expect(page).to_have_url("...")
- expect(page).to_have_text("...")
"""

    def _build_user_prompt(self, request: GenerationRequest) -> str:
        """构建用户提示"""
        prompt = f"""
# 测试任务

请根据以下测试用例生成 Playwright Python 测试代码：

## 测试环境
- Base URL: {request.base_url}
- 框架: Playwright (Python)
- 用例数量: {len(request.test_cases)}

## 测试用例

"""

        for i, tc in enumerate(request.test_cases, 1):
            prompt += f"""
### 用例 {i}: {tc.get('case_id')}
- **标题**: {tc.get('title')}
- **优先级**: {tc.get('priority')}
- **类型**: {tc.get('type')}

**前置条件**:
{chr(10).join(f"- {pre}" for pre in tc.get('preconditions', []))}

**测试步骤**:
"""
            for step in tc.get('steps', []):
                prompt += f"""
{step.get('step_num')}. {step.get('action')}
   预期: {step.get('expected')}
"""

            prompt += f"""
**预期结果**: {tc.get('expected_result')}

"""

        prompt += """
## 输出要求

请生成完整的 Python 测试代码，包括：
1. 所有必要的 import 语句
2. pytest fixtures (browser_context)
3. 所有测试函数
4. 适当的 setup/teardown

只返回代码，不要有其他解释。
"""

        return prompt

    def _extract_code(self, response: str) -> str:
        """从 LLM 响应中提取代码"""
        # 移除 markdown 代码块标记
        if "```python" in response:
            parts = response.split("```python")
            if len(parts) > 1:
                return parts[1].split("```")[0].strip()
        return response.strip()
```

### 3.2 测试执行器（Runner）

#### 3.2.1 本地执行器

```python
# qa/runner/local.py

import os
import sys
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Browser, Page
import traceback

from qa.runner.base import BaseRunner, TestConfig, TestResult
from qa.classifier.context_collector import ContextCollector
from qa.classifier.error_classifier import ErrorClassifier

@dataclass
class TestScript:
    """测试脚本"""
    path: Path
    name: str
    case_ids: List[str]

class LocalRunner(BaseRunner):
    """本地 Playwright 执行器（直接使用 Python Playwright API）"""

    def __init__(self, config: TestConfig):
        super().__init__(config)
        self.browser = None
        self.context = None
        self.page = None

    def check_environment(self) -> Dict[str, bool]:
        """检查本地环境"""
        checks = {}

        # 检查 Python 模块
        try:
            import playwright
            checks["playwright"] = True
        except ImportError:
            checks["playwright"] = False

        # 检查浏览器
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                p.chromium.launch(headless=True).close()
            checks["chromium"] = True
        except Exception as e:
            checks["chromium"] = False

        # 检查 pytest
        try:
            result = subprocess.run(
                ["pytest", "--version"],
                capture_output=True,
                timeout=5
            )
            checks["pytest"] = result.returncode == 0
        except:
            checks["pytest"] = False

        return checks

    async def execute_async(self) -> TestResult:
        """异步执行测试（内部方法）"""
        import time
        start_time = time.time()

        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "cases": [],
            "exit_code": 0,
        }

        try:
            # 1. 启动浏览器
            with sync_playwright() as p:
                self.browser = p.chromium.launch(
                    headless=self.config.headless,
                    args=['--no-sandbox', '--disable-dev-shm-usage'],
                )

                self.context = self.browser.new_context(
                    base_url=self.config.base_url,
                    record_video_dir=str(self.config.output_dir / "videos"),
                    record_trace_dir=str(self.config.output_dir / "traces"),
                )

                self.page = self.context.new_page()

                # 2. 设置默认超时
                self.page.set_default_timeout(30000)

                # 3. 执行测试脚本
                for script in self.config.scripts:
                    script_results = await self._execute_script(script)
                    results["cases"].extend(script_results)

                # 4. 汇总结果
                for case in results["cases"]:
                    results["total"] += 1
                    if case["status"] == "passed":
                        results["passed"] += 1
                    else:
                        results["failed"] += 1
                        if case["exit_code"] not in [0, 1]:
                            results["exit_code"] = 2

        except Exception as e:
            results["exit_code"] = 2
            results["error"] = str(e)
            traceback.print_exc()

        finally:
            # 清理资源
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()

        duration = int((time.time() - start_time) * 1000)

        return TestResult(
            exit_code=results["exit_code"],
            total=results["total"],
            passed=results["passed"],
            failed=results["failed"],
            report_path=self.config.output_dir / "results.json",
            duration_ms=duration,
        )

    def execute(self) -> TestResult:
        """同步执行测试（公共接口）"""
        return asyncio.run(self.execute_async())

    async def _execute_script(self, script: TestScript) -> List[Dict]:
        """执行单个测试脚本"""
        results = []

        # 动态导入测试模块
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "test_module",
            script.path
        )
        module = importlib.util.module_from_spec(spec)

        # 设置模块上下文
        module.page = self.page
        module.expect = expect  # 从 playwright 导入
        module.base_url = self.config.base_url

        # 执行测试函数
        for case_id in script.case_ids:
            test_func = getattr(module, f"test_{case_id}", None)
            if test_func:
                case_result = {
                    "case_id": case_id,
                    "status": "skipped",
                    "error": None,
                    "exit_code": 0,
                }

                try:
                    # 收集执行前上下文
                    context = ContextCollector.collect_before_test(self.page, "")

                    # 执行测试
                    test_func()

                    case_result["status"] = "passed"
                    case_result["exit_code"] = 0

                except AssertionError as e:
                    case_result["status"] = "failed"
                    case_result["error"] = str(e)
                    case_result["exit_code"] = 1

                    # 截图
                    screenshot_path = self.config.output_dir / "screenshots" / f"{case_id}.png"
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    self.page.screenshot(path=str(screenshot_path))

                except Exception as e:
                    case_result["status"] = "failed"
                    case_result["error"] = str(e)
                    case_result["exit_code"] = 2

                    # 错误分类
                    classification = ErrorClassifier.classify(
                        str(e),
                        context=context
                    )
                    case_result["error_type"] = classification.type
                    case_result["is_code_issue"] = (classification.type == "code_issue")

                results.append(case_result)

        return results
```

### 3.3 Docker 执行器（可选）

```python
# qa/runner/docker.py

import subprocess
from pathlib import Path
from typing import Dict

from qa.runner.base import BaseRunner, TestConfig, TestResult

class DockerRunner(BaseRunner):
    """Docker 容器执行器（可选）"""

    DOCKER_IMAGE = "lee-e2e-runner:latest"

    def check_environment(self) -> Dict[str, bool]:
        """检查 Docker 环境"""
        checks = {}

        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5
            )
            checks["docker"] = result.returncode == 0
        except:
            checks["docker"] = False

        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.DOCKER_IMAGE],
                capture_output=True,
                timeout=5
            )
            checks["image"] = result.returncode == 0
        except:
            checks["image"] = False

        return checks

    def execute(self) -> TestResult:
        """Docker 执行测试"""
        # 构建 docker 命令
        cmd = [
            "docker", "run", "--rm",
            "--name", f"lee-e2e-{self.config.suite}",
            "--network", "host",
            "-e", f"BASE_URL={self.config.base_url}",
            "-e", f"TEST_ENV={self.config.environment}",
            "-v", f"{self.config.scripts_dir}:/app/tests:ro",
            "-v", f"{self.config.output_dir}:/app/output",
            "-v", f"{self.config.evidence_dir}:/app/evidence",
            self.DOCKER_IMAGE,
            "pytest", "tests/", "-v",
        ]

        # 执行
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=600,
        )

        # 解析结果
        return self._parse_result(result)

    def _parse_result(self, result: subprocess.CompletedProcess) -> TestResult:
        """解析 Docker 执行结果"""
        # 解析 JSON 报告
        import json

        report_path = self.config.output_dir / "results.json"
        if report_path.exists():
            with open(report_path) as f:
                data = json.load(f)

            return TestResult(
                exit_code=result.returncode,
                total=data.get("total", 0),
                passed=data.get("passed", 0),
                failed=data.get("failed", 0),
                report_path=report_path,
                duration_ms=data.get("duration_ms", 0),
            )

        # 默认结果
        return TestResult(
            exit_code=result.returncode,
            total=0,
            passed=0,
            failed=0,
            report_path=self.config.output_dir / "results.json",
            duration_ms=0,
        )
```

---

## 四、LLM 代码生成质量保证

### 4.1 验证金字塔

```
┌─────────────────────────────────────────────────────────────────┐
│                      代码验证金字塔                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                   │
│                    ┌───────────────┐                             │
│                    │  L4: 运行时   │  ← 动态验证（实际执行）      │
│                    │   验证       │                             │
│                    │  - 错误分类   │                             │
│                    │  - 证据收集   │                             │
│                    └───────┬───────┘                             │
│                            │                                     │
│                    ┌───────────────┐                             │
│                    │  L3: 语义     │  ← 静态分析（代码审查）      │
│                    │   验证       │                             │
│                    │  - 选择器质量 │                             │
│                    │  - 超时配置   │                             │
│                    │  - 最佳实践   │                             │
│                    └───────┬───────┘                             │
│                            │                                     │
│                    ┌───────────────┐                             │
│                    │  L2: 语法     │  ← 编译检查（AST 解析）      │
│                    │   验证       │                             │
│                    │  - Python AST │                             │
│                    │  - 导入检查   │                             │
│                    │  - 语义检查   │                             │
│                    └───────┬───────┘                             │
│                            │                                     │
│                    ┌───────────────┐                             │
│                    │  L1: 结构     │  ← 结构验证（Schema 检查）    │
│                    │   验证       │                             │
│                    │  - 必需导入   │                             │
│                    │  - 必需函数   │                             │
│                    │  - 禁止模式   │                             │
│                    └───────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Layer 1: 结构验证

```python
# qa/validator/schema_validator.py

import re
from typing import List, Dict
from dataclasses import dataclass
from qa.validator.result import ValidationResult

class SchemaValidator:
    """结构验证器（Layer 1）"""

    # 必需的导入
    REQUIRED_IMPORTS = [
        "from playwright.sync_api import sync_playwright",
        "import pytest",
    ]

    # 必需的 pytest fixture
    REQUIRED_FIXTURES = [
        "browser_context",
    ]

    # 禁止的模式
    FORBIDDEN_PATTERNS = [
        (r"page\.wait_for_timeout\(\d+\)", "使用硬编码超时，用 wait_for_* 替代"),
        (r"time\.sleep\(", "禁止使用 time.sleep"),
        (r"\.click\(\)", "使用 locator.click() 而非 page.click()"),
    ]

    # 推荐的模式
    RECOMMENDED_PATTERNS = [
        (r"page\.locator\(", "使用 page.locator() 定位元素"),
        (r"expect\(", "使用 expect() 进行断言"),
        (r"data-testid[\s]*=", "使用 data-testid 选择器"),
    ]

    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        """验证代码结构"""
        result = ValidationResult()

        # 1. 检查必需导入
        for imp in cls.REQUIRED_IMPORTS:
            if imp not in code:
                result.add_error("missing_import", f"缺少必需导入: {imp}")

        # 2. 检查禁止模式
        for pattern, message in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                result.add_error("forbidden_pattern", message)

        # 3. 检查推荐模式
        for pattern, message in cls.RECOMMENDED_PATTERNS:
            if re.search(pattern, code):
                result.add_info("recommendation", message)

        # 4. 检查 test 函数
        test_functions = re.findall(r"def (test_\w+)\(", code)
        if not test_functions:
            result.add_error("no_test_functions", "没有找到测试函数")

        # 5. 检查 fixture
        fixtures = re.findall(r"@pytest\.fixture\((.*?)\)", code)
        fixture_names = [f.strip('"\'') for f in fixtures]
        for req_fixture in cls.REQUIRED_FIXTURES:
            if req_fixture not in fixture_names:
                result.add_warning("missing_fixture", f"缺少 fixture: {req_fixture}")

        return result
```

### 4.3 Layer 2: 语法验证

```python
# qa/validator/syntax_validator.py

import ast
import sys

class SyntaxValidator:
    """语法验证器（Layer 2）"""

    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        """验证 Python 语法和基本语义"""
        result = ValidationResult()

        try:
            # 1. AST 解析
            tree = ast.parse(code)

        except SyntaxError as e:
            result.add_error(
                "syntax_error",
                f"行 {e.lineno}: {e.msg}"
            )
            return result

        # 2. 语义检查
        checker = SemanticChecker()
        try:
            checker.visit(tree)
        except Exception as e:
            result.add_error("semantic_error", str(e))

        # 3. 添加检查器发现的问题
        for error in checker.errors:
            result.add_error("semantic", error)

        return result


class SemanticChecker(ast.NodeVisitor):
    """语义检查器"""

    def __init__(self):
        self.errors = []
        self.imports = set()
        self.test_functions = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 检查测试函数
        if node.name.startswith("test_"):
            self.test_functions.append(node.name)

            # 检查函数参数
            if "page" not in [arg.arg for arg in node.args.args]:
                self.errors.append(
                    f"测试函数 '{node.name}' 缺少 'page' 参数"
                )

            # 检查 docstring
            if not ast.get_docstring(node):
                self.errors.append(
                    f"测试函数 '{node.name}' 缺少 docstring"
                )

        self.generic_visit(node)
```

### 4.4 Layer 3: 语义验证

```python
# qa/validator/selector_validator.py

import re
from typing import Dict, List

class SelectorValidator:
    """选择器质量验证器（Layer 3）"""

    # 选择器稳定性评分
    STABILITY_SCORES = {
        r'\[data-testid[=\s]?["\']?\w+["\']?\]': 1.0,
        r'\[id[\s]*=[\s]*["\']?\w+["\']?\]': 0.9,
        r'\[role=[\s]*["\']?\w+["\']?\]': 0.8,
        r'\.[\w-]+': 0.5,
        r'text[\s]*=[\s]*["\'][^"\']+["\']': 0.4,
    }

    UNSTABLE_PATTERNS = [
        (r':nth-child\(\d+\)', "硬编码位置，元素变化会失效"),
        (r':first-child', "相对位置，不推荐"),
        (r'\.class-\w+', "动态类名，不稳定"),
        (r'\w+\.\w+\.\w+', "复杂 CSS 路径，不稳定"),
    ]

    @classmethod
    def validate_selector(cls, selector: str) -> Dict:
        """验证单个选择器"""
        result = {
            "selector": selector,
            "score": 0.0,
            "issues": [],
            "recommendations": [],
        }

        # 1. 检查不稳定模式
        for pattern, message in cls.UNSTABLE_PATTERNS:
            if re.search(pattern, selector):
                result["issues"].append(message)
                result["score"] -= 0.3

        # 2. 计算稳定性评分
        max_score = 0.0
        for pattern, score in cls.STABILITY_SCORES.items():
            if re.search(pattern, selector):
                max_score = max(max_score, score)

        result["score"] = max(0.0, min(1.0, max_score + result["score"]))

        # 3. 生成推荐
        if result["score"] < 0.7:
            result["recommendations"].append(
                "建议使用 data-testid 属性，并添加到页面元素上"
            )

        return result

    @classmethod
    def validate_selectors_in_code(cls, code: str) -> Dict:
        """验证代码中的所有选择器"""
        selectors = re.findall(r'locator\(["\']([^"\']+)["\']\)', code)

        results = {
            "total": len(selectors),
            "avg_score": 0.0,
            "low_score_selectors": [],
        }

        scores = []
        for selector in selectors:
            selector_result = cls.validate_selector(selector)
            scores.append(selector_result["score"])

            if selector_result["score"] < 0.7:
                results["low_score_selectors"].append(selector_result)

        if scores:
            results["avg_score"] = sum(scores) / len(scores)

        return results
```

```python
# qa/validator/timeout_validator.py

class TimeoutValidator:
    """超时配置验证器（Layer 3）"""

    DEFAULT_TIMEOUT = 30000
    MAX_TIMEOUT = 60000

    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        """验证超时配置"""
        result = ValidationResult()

        # 查找超时配置
        patterns = {
            r'set_default_timeout\((\d+)\)': "default_timeout",
            r'goto\([^,]+,\s*timeout=(\d+)\)': "goto_timeout",
            r'wait_for_selector\([^,]+,\s*timeout=(\d+)\)': "wait_timeout",
            r'wait_for_load_state\([^,]+,\s*timeout=(\d+)\)': "load_timeout",
        }

        timeouts = {}
        for pattern, name in patterns.items():
            matches = re.findall(pattern, code)
            for match in matches:
                timeouts[name] = int(match)

        # 检查默认超时
        if "default_timeout" in timeouts:
            if timeouts["default_timeout"] < 5000:
                result.add_warning(
                    "timeout_too_short",
                    f"默认超时 {timeouts['default_timeout']}ms 可能太短"
                )
            elif timeouts["default_timeout"] > cls.MAX_TIMEOUT:
                result.add_error(
                    "timeout_too_long",
                    f"默认超时 {timeouts['default_timeout']}ms 超过最大值"
                )
        else:
            result.add_warning(
                "no_default_timeout",
                "未设置默认超时，建议使用 set_default_timeout()"
            )

        # 检查 goto 超时
        if "goto_timeout" in timeouts:
            if timeouts["goto_timeout"] < 10000:
                result.add_warning(
                    "goto_timeout_short",
                    "page.goto() 超时应该至少 10000ms（等待网络）"
                )

        return result
```

---

## 五、错误分类与诊断

### 5.1 错误分类器

```python
# qa/classifier/error_classifier.py

from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

class ErrorType(Enum):
    """错误类型"""
    CODE_SYNTAX = "code_syntax"           # 语法错误
    CODE_IMPORT = "code_import"           # 导入错误
    CODE_API = "code_api"                 # API 使用错误
    CODE_TIMEOUT = "code_timeout"         # 超时配置不当
    CODE_SELECTOR = "code_selector"       # 选择器错误

    SYSTEM_ASSERTION = "system_assertion" # 断言失败
    SYSTEM_NETWORK = "system_network"     # 网络错误
    SYSTEM_SERVER = "system_server"       # 服务器错误
    SYSTEM_DATA = "system_data"           # 数据问题

    UNCERTAIN = "uncertain"                # 不确定


@dataclass
class ErrorClassification:
    """错误分类结果"""
    type: str  # code_issue / system_issue / uncertain
    category: str  # 具体分类
    confidence: float  # 0-1，置信度
    is_false_fail: bool  # 是否为假失败
    suggested_action: str  # 建议操作
    explanation: str  # 解释


class ErrorClassifier:
    """错误分类器"""

    # 代码问题模式
    CODE_PATTERNS = {
        # 语法/导入
        r"SyntaxError": ErrorType.CODE_SYNTAX,
        r"IndentationError": ErrorType.CODE_SYNTAX,
        r"ModuleNotFoundError: no module named 'playwright'": ErrorType.CODE_IMPORT,
        r"NameError: name '(\w+)' is not defined": ErrorType.CODE_API,

        # API 使用
        r"AttributeError: 'Locator' object has no attribute 'wait_for'": ErrorType.CODE_API,
        r"TypeError: object of type.*has no len\(\)": ErrorType.CODE_API,

        # 选择器
        r"Timeout.*waiting for selector.*strict mode violation": ErrorType.CODE_SELECTOR,
        r"Timeout.*waiting for selector.*waiting for hidden": ErrorType.CODE_SELECTOR,
        r"playwright\.sync_api\.errors.TimeoutError.*waiting for.*": ErrorType.CODE_SELECTOR,
    }

    # 系统问题模式
    SYSTEM_PATTERNS = {
        # 断言失败
        r"AssertionError": ErrorType.SYSTEM_ASSERTION,
        r"assert.*failed": ErrorType.SYSTEM_ASSERTION,

        # 网络
        r"NET::ERR_CONNECTION_REFUSED": ErrorType.SYSTEM_NETWORK,
        r"NET::ERR_TIMED_OUT": ErrorType.SYSTEM_NETWORK,
        r"Timeout.*exceeded.*": ErrorType.SYSTEM_NETWORK,

        # 服务器
        r"Status.*5\d\d": ErrorType.SYSTEM_SERVER,

        # 数据
        r"Expected.*but found": ErrorType.SYSTEM_DATA,
    }

    @classmethod
    def classify(
        cls,
        error_message: str,
        context: Optional[Dict] = None
    ) -> ErrorClassification:
        """分类错误"""
        import re

        error_lower = error_message.lower()

        # 1. 检查代码问题模式
        for pattern, error_type in cls.CODE_PATTERNS.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return cls._create_code_classification(
                    error_type, error_message, context
                )

        # 2. 检查系统问题模式
        for pattern, error_type in cls.SYSTEM_PATTERNS.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return cls._create_system_classification(
                    error_type, error_message, context
                )

        # 3. 不确定错误 - 用上下文辅助判断
        return cls._classify_uncertain(error_message, context)

    @classmethod
    def _create_code_classification(
        cls,
        error_type: ErrorType,
        error_message: str,
        context: Dict
    ) -> ErrorClassification:
        """创建代码问题分类"""
        return ErrorClassification(
            type="code_issue",
            category=error_type.value,
            confidence=0.9,
            is_false_fail=True,
            suggested_action="auto_fix",  # 尝试自动修复
            explanation="这是测试代码的问题，不是被测系统的Bug",
        )

    @classmethod
    def _create_system_classification(
        cls,
        error_type: ErrorType,
        error_message: str,
        context: Dict
    ) -> ErrorClassification:
        """创建系统问题分类"""
        return ErrorClassification(
            type="system_issue",
            category=error_type.value,
            confidence=0.85,
            is_false_fail=False,
            suggested_action="file_bug",
            explanation="这是被测系统的问题，需要创建Bug",
        )

    @classmethod
    def _classify_uncertain(
        cls,
        error_message: str,
        context: Optional[Dict]
    ) -> ErrorClassification:
        """分类不确定错误"""
        # 用上下文信息辅助判断
        if context:
            # 检查选择器是否存在
            selector = context.get("selector", "")
            page_elements = context.get("page_elements", {})

            if selector and selector in page_elements:
                # 选择器存在但超时 → 可能是时序问题
                return ErrorClassification(
                    type="uncertain",
                    category="timing",
                    confidence=0.6,
                    is_false_fail=False,
                    suggested_action="add_wait",
                    explanation="元素存在但超时，可能是加载延迟问题",
                )
            elif selector and selector not in page_elements:
                # 选择器不存在 → 可能是代码选择器错误
                return ErrorClassification(
                    type="code_issue",
                    category="selector_not_found",
                    confidence=0.6,
                    is_false_fail=True,
                    suggested_action="verify_selector",
                    explanation="选择器在页面中未找到，可能是选择器错误",
                )

        # 默认：不确定
        return ErrorClassification(
            type="uncertain",
            category="unknown",
            confidence=0.0,
            is_false_fail=None,
            suggested_action="manual_review",
            explanation="无法自动判断，需要人工审查",
        )
```

### 5.2 上下文收集器

```python
# qa/classifier/context_collector.py

from playwright.sync_api import Page
from typing import Dict, List

class ContextCollector:
    """运行时上下文收集器"""

    @staticmethod
    def collect_before_test(page: Page, selector: str) -> Dict:
        """在测试执行前收集上下文"""
        return {
            "page_url": page.url,
            "page_title": page.title(),
            "selector_exists": ContextCollector._selector_exists(page, selector),
            "page_elements": ContextCollector._extract_elements(page),
        }

    @staticmethod
    def collect_on_error(page: Page) -> Dict:
        """在错误发生时收集额外上下文"""
        return {
            "page_url": page.url,
            "page_title": page.title(),
            "screenshot_taken": True,  # 标记截图已保存
            "console_logs": ContextCollector._get_console_logs(page),
        }

    @staticmethod
    def _selector_exists(page: Page, selector: str) -> bool:
        """检查选择器是否存在"""
        try:
            locator = page.locator(selector)
            return locator.count() > 0
        except:
            return False

    @staticmethod
    def _extract_elements(page: Page) -> Dict[str, Dict]:
        """提取页面上所有可交互元素"""
        elements = {}

        try:
            # 提取所有带 data-testid 的元素
            testids = page.locator("[data-testid]").all()
            for el in testids:
                try:
                    tid = el.get_attribute("data-testid")
                    if tid:
                        elements[f"[data-testid='{tid}']"] = {
                            "tag": el.evaluate("el => el.tagName"),
                            "text": el.evaluate("el => el.textContent?.trim() || ''"),
                        }
                except:
                    pass
        except:
            pass

        return elements

    @staticmethod
    def _get_console_logs(page: Page) -> List[str]:
        """获取控制台日志"""
        # TODO: 实现控制台日志收集
        return []
```

### 5.3 自动修复器

```python
# qa/fixer/auto_fixer.py

from typing import Dict, Optional
import re

class AutoFixer:
    """自动修复器"""

    @staticmethod
    def fix_selector(code: str, bad_selector: str, context: Dict) -> str:
        """修复选择器问题"""
        # 从上下文中找推荐的选择器
        similar_selectors = context.get("similar_selectors", [])

        if similar_selectors:
            # 用最相似的选择器替换
            new_selector = similar_selectors[0]
            code = re.sub(
                f'locator\\(["\']?{re.escape(bad_selector)}["\']?\\)',
                f'locator("{new_selector}")',
                code
            )

        return code

    @staticmethod
    def fix_timeout(code: str, timeout_location: str) -> str:
        """修复超时问题"""
        # 增加超时时间
        if timeout_location == "default":
            code = re.sub(
                r'set_default_timeout\((\d+)\)',
                lambda m: f'set_default_timeout({max(int(m.group(1)) * 2, 60000)})',
                code
            )
        return code

    @staticmethod
    def fix_import(code: str, missing_import: str) -> str:
        """修复导入问题"""
        # 添加缺失的导入
        import_line = f"from playwright.sync_api import {missing_import}"

        # 在第一个 import 语句前添加
        import_match = re.search(r'^(import |from )', code, re.MULTILINE)
        if import_match:
            insert_pos = import_match.start()
            code = code[:insert_pos] + import_line + "\n" + code[insert_pos:]
        else:
            code = import_line + "\n\n" + code

        return code
```

---

## 六、实施计划

### 6.1 时间估算

| 模块 | 预估时间 | 依赖 |
|------|----------|------|
| **核心框架** | | |
| ├── Generator 基类 + PlaywrightGen | 0.5天 | 无 |
| ├── Runner 基类 + LocalRunner | 1天 | playwright |
| ├── DockerRunner（可选） | 0.5天 | docker |
| **质量保证** | | |
| ├── SchemaValidator | 0.5天 | 无 |
| ├── SyntaxValidator | 0.5天 | ast |
| ├── SelectorValidator | 0.5天 | 无 |
| └── TimeoutValidator | 0.5天 | 无 |
| **错误分类** | | |
| ├── ErrorClassifier | 1天 | 无 |
| ├── ContextCollector | 0.5天 | playwright |
| └── AutoFixer | 0.5天 | 无 |
| **单元测试** | | |
| ├── Generator 测试 | 0.5天 | Generator |
| ├── Validator 测试 | 0.5天 | Validator |
| ├── Classifier 测试 | 0.5天 | Classifier |
| ├── Runner 测试 | 0.5天 | Runner |
| ├── Mock 数据建设 | 0.5天 | 无 |
| **系统集成** | | |
| ├── L3 工作流集成 | 1天 | 所有模块 |
| ├── Agent 对接测试 | 0.5天 | Orchestrator |
| ├── 端到端测试 | 0.5天 | 所有模块 |
| ├── 性能测试 | 0.5天 | 无 |
| **代码评审** | | |
| ├── 第一轮评审（设计） | 0.5天 | 设计完成 |
| ├── 第二轮评审（核心实现） | 0.5天 | 核心模块完成 |
| ├── 第三轮评审（集成验证） | 0.5天 | 集成完成 |
| ├── 评审意见修复 | 0.5天 | 评审反馈 |
| **文档与交付** | | |
| ├── API 文档 | 0.5天 | 无 |
| ├── 用户手册 | 0.5天 | 无 |
| ├── Bug 修复 | 0.5天 | - |
| **总计** | **11-13 天** | - |

### 6.2 实施顺序

```
Week 1: 核心框架 + 单元测试
├── Day 1: Generator + Validator 基础
├── Day 2: LocalRunner 实现
├── Day 3: 单元测试（Generator + Validator）
├── Day 4: Classifier + AutoFixer
└── Day 5: 单元测试（Classifier + Runner）

Week 2: 系统集成 + 代码评审
├── Day 6: L3 工作流集成
├── Day 7: Agent 对接 + 端到端测试
├── Day 8: 性能测试 + 优化
├── Day 9: 第一轮代码评审（设计+架构）
├── Day 10: 第二轮代码评审（核心实现）
└── Day 11: 第三轮代码评审（集成验证）

Week 3: 修复与交付
├── Day 12: 评审意见修复 + Bug 修复
└── Day 13: 文档完善 + 交付
```

### 6.3 里程碑

| 里程碑 | 标准 | 验收方式 |
|--------|------|----------|
| M1: 代码生成 | LLM 能生成通过语法验证的代码 | 单元测试通过 |
| M2: 本地执行 | 能在本地执行简单测试 | 手动验证 |
| M3: 错误分类 | 能区分代码/系统问题，准确率 > 80% | 单元测试 + 人工验证 |
| M4: 自动修复 | 能自动修复常见的代码问题 | 单元测试 |
| M5: 单元测试覆盖 | 覆盖率 ≥ 80% | pytest-cov 报告 |
| M6: 系统集成 | L3 工作流端到端跑通 | 集成测试 |
| M7: 性能达标 | 单个用例执行 < 30s | 性能测试 |
| M8: 代码评审通过 | 三轮评审无重大问题 | 评审记录 |
| M9: 完整闭环 | 端到端流程跑通 + 文档齐全 | 验收测试 |

---

### 6.4 单元测试策略

#### 6.4.1 测试目录结构

```
tests/qa/
├── __init__.py
├── conftest.py                          # pytest fixtures
├── fixtures/                            # 测试数据
│   ├── test_cases.yaml                 # 模拟测试用例
│   ├── generated_code/                 # 模拟生成的代码
│   │   ├── valid_code.py
│   │   ├── syntax_error.py
│   │   ├── bad_selector.py
│   │   └── timeout_issue.py
│   └── runner_outputs/                 # 模拟执行结果
│       ├── success.json
│       ├── failure.json
│       └── error.json
├── generator/                           # Generator 测试
│   ├── __init__.py
│   ├── test_base.py
│   ├── test_playwright_gen.py
│   └── test_templates.py
├── validator/                           # Validator 测试
│   ├── __init__.py
│   ├── test_schema_validator.py
│   ├── test_syntax_validator.py
│   ├── test_selector_validator.py
│   └── test_timeout_validator.py
├── classifier/                          # Classifier 测试
│   ├── __init__.py
│   ├── test_error_classifier.py
│   ├── test_patterns.py
│   └── test_context_collector.py
├── runner/                              # Runner 测试
│   ├── __init__.py
│   ├── test_base.py
│   ├── test_local_runner.py
│   └── test_docker_runner.py
└── integration/                         # 集成测试
    ├── __init__.py
    ├── test_workflow.py
    └── test_e2e.py
```

#### 6.4.2 测试用例设计

**Generator 测试**

```python
# tests/qa/generator/test_playwright_gen.py

import pytest
from qa.generator.playwright_gen import PlaywrightGenerator
from qa.generator.base import GenerationRequest

class TestPlaywrightGenerator:
    """Playwright 生成器测试"""

    @pytest.fixture
    def generator(self, mock_llm_client):
        return PlaywrightGenerator(llm_client=mock_llm_client)

    @pytest.fixture
    def sample_request(self):
        return GenerationRequest(
            test_cases=[{
                "case_id": "F-BASE-002",
                "title": "开发测试登录",
                "priority": "P0",
                "steps": [
                    {"step_num": 1, "action": "访问登录页", "expected": "页面加载"},
                    {"step_num": 2, "action": "点击登录", "expected": "登录成功"},
                ],
                "expected_result": "用户登录成功",
            }],
            base_url="http://localhost:3000",
        )

    def test_generate_returns_code(self, generator, sample_request):
        """测试生成代码"""
        result = generator.generate(sample_request)
        assert result.code is not None
        assert len(result.code) > 0

    def test_generate_includes_imports(self, generator, sample_request):
        """测试生成代码包含必需导入"""
        result = generator.generate(sample_request)
        assert "from playwright.sync_api import" in result.code
        assert "import pytest" in result.code

    def test_generate_includes_test_functions(self, generator, sample_request):
        """测试生成代码包含测试函数"""
        result = generator.generate(sample_request)
        assert "def test_" in result.code

    def test_validation_on_syntax_error(self, generator, sample_request, mock_llm_syntax_error):
        """测试语法错误时重试"""
        result = generator.generate(sample_request)
        assert result.validation.is_valid
        assert result.retries > 0

    def test_max_retries_exceeded(self, generator, sample_request, mock_llm_always_error):
        """测试超过最大重试次数"""
        with pytest.raises(CodeGenerationError):
            generator.generate(sample_request)
```

**Validator 测试**

```python
# tests/qa/validator/test_syntax_validator.py

import pytest
from qa.validator.syntax_validator import SyntaxValidator

class TestSyntaxValidator:
    """语法验证器测试"""

    def test_valid_code_passes(self):
        """测试有效代码通过验证"""
        code = """
import pytest
from playwright.sync_api import sync_playwright

def test_example(page):
    assert page.title() == "Example"
"""
        result = SyntaxValidator.validate(code)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_syntax_error_detected(self):
        """测试检测语法错误"""
        code = "def test(\n"  # 语法错误
        result = SyntaxValidator.validate(code)
        assert not result.is_valid
        assert any(e["type"] == "syntax_error" for e in result.errors)

    def test_missing_page_parameter(self):
        """测试检测缺少 page 参数"""
        code = """
def test_example():  # 缺少 page 参数
    pass
"""
        result = SyntaxValidator.validate(code)
        assert not result.is_valid
        assert any("page" in e.get("message", "") for e in result.errors)

    def test_missing_docstring(self):
        """测试检测缺少 docstring"""
        code = "def test_example(page):\n    pass"
        result = SyntaxValidator.validate(code)
        assert not result.is_valid
        assert any("docstring" in e.get("message", "") for e in result.errors)
```

**Classifier 测试**

```python
# tests/qa/classifier/test_error_classifier.py

import pytest
from qa.classifier.error_classifier import ErrorClassifier, ErrorType

class TestErrorClassifier:
    """错误分类器测试"""

    @pytest.mark.parametrize("error_message,expected_type", [
        ("SyntaxError: invalid syntax", ErrorType.CODE_SYNTAX),
        ("ModuleNotFoundError: no module named 'playwright'", ErrorType.CODE_IMPORT),
        ("Timeout waiting for selector", ErrorType.CODE_SELECTOR),
        ("AssertionError: Expected true but got false", ErrorType.SYSTEM_ASSERTION),
        ("NET::ERR_CONNECTION_REFUSED", ErrorType.SYSTEM_NETWORK),
    ])
    def test_classification_patterns(self, error_message, expected_type):
        """测试错误分类模式"""
        result = ErrorClassifier.classify(error_message)
        assert result.category == expected_type.value

    def test_code_issue_is_false_fail(self):
        """测试代码问题是假失败"""
        result = ErrorClassifier.classify("SyntaxError: invalid syntax")
        assert result.is_false_fail is True
        assert result.suggested_action == "auto_fix"

    def test_system_issue_is_true_fail(self):
        """测试系统问题是真失败"""
        result = ErrorClassifier.classify("AssertionError: Expected X but got Y")
        assert result.is_false_fail is False
        assert result.suggested_action == "file_bug"

    def test_uncertain_classification(self):
        """测试不确定错误分类"""
        result = ErrorClassifier.classify("Unknown error occurred")
        assert result.type == "uncertain"
        assert result.suggested_action == "manual_review"
```

#### 6.4.3 Mock 数据建设

```python
# tests/qa/conftest.py

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path

@pytest.fixture
def mock_llm_client():
    """Mock LLM 客户端"""
    mock = Mock()
    mock.complete.return_value = """
```python
import pytest
from playwright.sync_api import sync_playwright, expect

@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        yield page
        browser.close()

def test_example(page):
    '''Test example'''
    page.goto("http://localhost:3000")
    expect(page).to_have_title("Example")
```
"""
    return mock

@pytest.fixture
def mock_llm_syntax_error(mock_llm_client):
    """Mock LLM 返回语法错误（第一次）"""
    call_count = [0]
    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return "```python\ndef test(\n```"  # 语法错误
        return mock_llm_client.complete(*args, **kwargs)
    mock_llm_client.complete.side_effect = side_effect
    return mock_llm_client

@pytest.fixture
def sample_test_case():
    """示例测试用例"""
    return {
        "case_id": "F-BASE-002",
        "title": "开发测试登录",
        "priority": "P0",
        "type": "positive",
        "preconditions": ["用户未登录"],
        "steps": [
            {"step_num": 1, "action": "访问登录页", "expected": "页面加载"},
            {"step_num": 2, "action": "点击登录", "expected": "登录成功"},
        ],
        "expected_result": "用户登录成功",
    }
```

#### 6.4.4 测试覆盖率目标

| 模块 | 覆盖率目标 | 重点 |
|------|------------|------|
| generator/ | ≥ 85% | LLM 调用、重试逻辑 |
| validator/ | ≥ 90% | 各种错误模式 |
| classifier/ | ≥ 85% | 分类准确性 |
| runner/ | ≥ 75% | 执行逻辑、错误处理 |
| fixer/ | ≥ 80% | 修复策略 |
| **总体** | **≥ 80%** | - |

---

### 6.5 系统集成测试

#### 6.5.1 L3 工作流集成

**集成点验证**

```python
# tests/qa/integration/test_workflow.py

import pytest
from pathlib import Path
import yaml

class TestL3WorkflowIntegration:
    """L3 工作流集成测试"""

    @pytest.fixture
    def test_set_definition(self):
        """加载 Test Set 定义"""
        return yaml.safe_load("""
id: test-set-001
name: 登录功能测试集
type: e2e_chrome
base_url: http://localhost:3000
cases:
  - case_id: F-BASE-002
    title: 开发测试登录
    priority: P0
""")

    def test_script_generation_integration(self, test_set_definition):
        """测试脚本生成集成"""
        from qa.generator.playwright_gen import PlaywrightGenerator

        generator = PlaywrightGenerator()
        request = GenerationRequest(
            test_cases=test_set_definition["cases"],
            base_url=test_set_definition["base_url"],
        )

        result = generator.generate(request)
        assert result.validation.is_valid
        assert "def test_" in result.code

    def test_runner_execution_integration(self, tmp_path):
        """测试执行器集成"""
        from qa.runner.local import LocalRunner
        from qa.runner.base import TestConfig

        # 创建临时脚本
        script_path = tmp_path / "test_script.py"
        script_path.write_text("""
import pytest
from playwright.sync_api import sync_playwright

def test_simple():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("about:blank")
        assert page.title() == ""
        browser.close()
""")

        config = TestConfig(
            scripts=[script_path],
            base_url="about:blank",
            output_dir=tmp_path / "output",
            headless=True,
        )

        runner = LocalRunner(config)
        result = runner.execute()

        assert result.exit_code == 0
        assert result.total == 1

    def test_classifier_integration(self):
        """测试分类器集成"""
        from qa.classifier.error_classifier import ErrorClassifier

        test_errors = [
            ("SyntaxError", "code_issue", True),
            ("AssertionError", "system_issue", False),
            ("Timeout", "code_issue", True),
        ]

        for error_msg, expected_type, expected_false_fail in test_errors:
            result = ErrorClassifier.classify(error_msg)
            assert result.type == expected_type
            assert result.is_false_fail == expected_false_fail
```

#### 6.5.2 Agent 对接测试

**Script Translator Agent 对接**

```yaml
# tests/qa/fixtures/agent_script_translator_test.yaml
# 用于验证 agent.qa.script_translator 能正确调用生成器

test_case:
  input:
    agent: "agent.qa.script_translator"
    input:
      generated_cases:
        - case_id: "F-BASE-002"
          title: "开发测试登录"
          priority: "P0"
      environment:
        base_url: "http://localhost:3000"
      test_set:
        type: "e2e_chrome"

  expected_output:
    test_scripts:
      - path: "scripts/test_f_base_002.py"
        framework: "playwright"
        status: "generated"
```

**Result Judge Agent 对接**

```yaml
# tests/qa/fixtures/agent_result_judge_test.yaml
# 用于验证 agent.qa.result_judge 能正确使用分类器

test_case:
  input:
    agent: "agent.qa.result_judge"
    input:
      runner_output:
        cases:
          - case_id: "F-BASE-002"
            status: "failed"
            error: "SyntaxError: invalid syntax"
      expected_results:
        - case_id: "F-BASE-002"
          expected: "登录成功"

  expected_output:
    results:
      - case_id: "F-BASE-002"
        status: "invalid_run"
        error_type: "code_issue"
        is_false_fail: true
```

#### 6.5.3 端到端测试

```python
# tests/qa/integration/test_e2e.py

import pytest
import tempfile
import shutil
from pathlib import Path

class TestE2E:
    """端到端测试"""

    @pytest.fixture
    def workspace(self, tmp_path):
        """创建临时工作空间"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_full_pipeline(self, workspace):
        """测试完整流程：用例 → 脚本 → 执行 → 判定"""
        from qa.generator.playwright_gen import PlaywrightGenerator
        from qa.runner.local import LocalRunner
        from qa.classifier.error_classifier import ErrorClassifier

        # 1. 生成脚本
        request = GenerationRequest(
            test_cases=[{
                "case_id": "F-BASE-001",
                "title": "简单页面访问",
                "priority": "P0",
                "steps": [{"step_num": 1, "action": "访问 about:blank", "expected": "页面加载"}],
                "expected_result": "页面加载成功",
            }],
            base_url="about:blank",
        )

        generator = PlaywrightGenerator()
        gen_result = generator.generate(request)
        assert gen_result.validation.is_valid

        # 2. 保存脚本
        script_path = workspace / "test_script.py"
        script_path.write_text(gen_result.code)

        # 3. 执行测试
        from qa.runner.base import TestConfig
        config = TestConfig(
            scripts=[script_path],
            base_url="about:blank",
            output_dir=workspace / "output",
            headless=True,
        )

        runner = LocalRunner(config)
        run_result = runner.execute()

        # 4. 验证结果
        assert run_result.exit_code == 0
        assert run_result.passed > 0

    def test_error_classification_flow(self, workspace):
        """测试错误分类流程"""
        # 生成一个有错误的脚本
        bad_code = """
def test_with_error(page):
    page.locator("[data-testid='non-existent']").click()
"""

        script_path = workspace / "bad_script.py"
        script_path.write_text(bad_code)

        # 执行并分类错误
        # ... 执行逻辑 ...

        # 验证分类结果
        # 模拟错误分类
        classification = ErrorClassifier.classify(
            "Timeout waiting for selector [data-testid='non-existent']"
        )

        assert classification.type in ["code_issue", "uncertain"]
        assert classification.suggested_action in ["auto_fix", "verify_selector"]
```

#### 6.5.4 性能测试

```python
# tests/qa/integration/test_performance.py

import pytest
import time

class TestPerformance:
    """性能测试"""

    @pytest.mark.performance
    def test_code_generation_performance(self):
        """测试代码生成性能"""
        from qa.generator.playwright_gen import PlaywrightGenerator

        generator = PlaywrightGenerator()
        request = GenerationRequest(
            test_cases=[{"case_id": "F-001", "title": "测试", "priority": "P0", "steps": [], "expected_result": ""}],
            base_url="http://localhost:3000",
        )

        start = time.time()
        result = generator.generate(request)
        duration = time.time() - start

        # 代码生成应在 30 秒内完成（含 LLM 调用）
        assert duration < 30

    @pytest.mark.performance
    def test_validation_performance(self):
        """测试验证性能"""
        from qa.validator.syntax_validator import SyntaxValidator

        # 生成一个较大的代码文件
        large_code = "def test_{}(page):\n    pass\n" * 1000

        start = time.time()
        result = SyntaxValidator.validate(large_code)
        duration = time.time() - start

        # 验证应在 1 秒内完成
        assert duration < 1

    @pytest.mark.performance
    def test_classification_performance(self):
        """测试分类性能"""
        from qa.classifier.error_classifier import ErrorClassifier

        start = time.time()
        for _ in range(1000):
            ErrorClassifier.classify("SyntaxError: invalid syntax")
        duration = time.time() - start

        # 1000 次分类应在 1 秒内完成
        assert duration < 1
```

---

### 6.6 代码评审流程

#### 6.6.1 评审轮次与内容

| 轮次 | 时机 | 评审重点 | 参与者 | 通过标准 |
|------|------|----------|--------|----------|
| **R1: 设计评审** | 设计完成后 | 架构合理性、模块划分、接口设计 | 架构师 + Tech Lead | 设计文档批准 |
| **R2: 核心实现评审** | 核心模块完成后 | 代码质量、错误处理、测试覆盖 | Tech Lead + 开发团队 | 核心代码批准 |
| **R3: 集成评审** | 集成完成后 | 集成质量、端到端验证、性能 | 全团队 + QA | 集成测试通过 |

#### 6.6.2 评审检查清单

**设计评审（R1）**

```markdown
## 设计评审检查清单

### 架构设计
- [ ] 模块职责是否清晰？
- [ ] 模块间依赖是否合理？
- [ ] 接口抽象是否恰当？
- [ ] 扩展性是否足够？

### 技术选型
- [ ] 依赖库是否成熟稳定？
- [ ] 是否有替代方案？
- [ ] 版本兼容性如何？

### 风险评估
- [ ] 潜在风险是否识别？
- [ ] 是否有缓解措施？
- [ ] 时间估算是否合理？

### 文档质量
- [ ] 设计文档是否完整？
- [ ] 接口文档是否清晰？
- [ ] 示例代码是否正确？
```

**核心实现评审（R2）**

```markdown
## 核心实现评审检查清单

### 代码质量
- [ ] 代码风格是否一致？
- [ ] 命名是否清晰？
- [ ] 注释是否充分？
- [ ] 是否有代码重复？

### 错误处理
- [ ] 异常是否被正确捕获？
- [ ] 错误信息是否清晰？
- [ ] 是否有资源泄漏？

### 测试覆盖
- [ ] 单元测试是否充分？
- [ ] 边界条件是否测试？
- [ ] 异常路径是否测试？
- [ ] Mock 是否合理？

### 性能考虑
- [ ] 是否有明显性能问题？
- [ ] 是否有不必要的重复计算？
- [ ] 资源使用是否高效？
```

**集成评审（R3）**

```markdown
## 集成评审检查清单

### 集成质量
- [ ] 模块间集成是否正确？
- [ ] 数据流转是否正确？
- [ ] 错误传播是否正确？

### 端到端验证
- [ ] 完整流程是否跑通？
- [ ] L3 工作流是否能正常执行？
- [ ] Agent 对接是否正确？

### 性能验证
- [ ] 性能指标是否达标？
- [ ] 是否有性能瓶颈？
- [ ] 是否有内存泄漏？

### 文档完整性
- [ ] API 文档是否完整？
- [ ] 用户手册是否清晰？
- [ ] 部署文档是否详细？
```

#### 6.6.3 评审意见追踪

```python
# 评审意见追踪表（示例）

review_comments = [
    {
        "id": "R1-001",
        "round": "R1",
        "category": "架构",
        "severity": "major",
        "comment": "Generator 和 Validator 的职责边界不够清晰",
        "proposed_by": "架构师A",
        "status": "resolved",
        "resolution": "明确接口契约，Validator 只负责验证不负责生成",
    },
    {
        "id": "R2-001",
        "round": "R2",
        "category": "代码质量",
        "severity": "minor",
        "comment": "ErrorClassifier 的模式匹配缺少对多行错误的支持",
        "proposed_by": "Tech Lead B",
        "status": "resolved",
        "resolution": "增加多行模式匹配支持",
    },
    {
        "id": "R3-001",
        "round": "R3",
        "category": "性能",
        "severity": "major",
        "comment": "LocalRunner 每次都启动新浏览器，性能较差",
        "proposed_by": "QA C",
        "status": "open",
        "resolution": "待优化",
    },
]
```

#### 6.6.4 评审通过标准

```yaml
# 评审通过标准定义

approval_criteria:
  R1_design_review:
    required_approvers: 2  # 至少 2 人批准
    veto_power: [架构师]   # 架构师有一票否决权
    block_issues:
      - severity: major
        count: 0  # 不能有 major 问题
      - severity: minor
        count: 3  # 最多 3 个 minor 问题

  R2_core_implementation_review:
    required_approvers: 2
    veto_power: [Tech Lead]
    block_issues:
      - severity: critical
        count: 0
      - severity: major
        count: 1  # 最多 1 个 major 问题
    code_coverage_threshold: 80  # 代码覆盖率必须 ≥ 80%

  R3_integration_review:
    required_approvers: 3  # 需要更多人批准
    veto_power: []
    block_issues:
      - severity: critical
        count: 0
      - severity: major
        count: 0  # 不能有 major 问题
    must_pass_tests:
      - unit_tests
      - integration_tests
      - e2e_tests
    performance_threshold:
      code_generation: 30s
      test_execution: 60s
```

---

## 七、风险评估

### 7.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **LLM 生成代码质量不稳定** | 高 | 高 | 多层验证 + 重试机制 |
| **错误分类准确率不达标** | 中 | 高 | 持续优化 + 人工审核兜底 |
| **Playwright API 兼容性** | 低 | 中 | 版本锁定 + 兼容性测试 |
| **性能问题** | 低 | 低 | 异步执行 + 并行优化 |

### 7.2 设计风险

| 风险 | 缓解措施 |
|------|----------|
| **过度设计** | 简化抽象层，优先实现功能 |
| **扩展性不足** | 预留接口，支持多框架 |
| **维护成本** | 充分文档，单元测试覆盖 |

### 7.3 质量目标

| 指标 | 目标值 | 验收方式 |
|------|--------|----------|
| 代码生成通过率（3次重试内） | ≥ 95% | 单元测试 |
| 语法验证通过率 | 100% | 自动检查 |
| 错误分类准确率 | ≥ 85% | 人工验证 |
| 假失败率 | < 5% | 统计分析 |
| 端到端执行成功率 | ≥ 90% | 集成测试 |

---

## 八、附录

### 8.1 关键设计决策记录

| 决策 | 理由 | 替代方案 |
|------|------|----------|
| **Python Playwright 而非 subprocess → npx** | 避免跨语言边界，简化调试 | subprocess 调用 Node.js |
| **本地执行优先，Docker 可选** | 开发体验，降低门槛 | 强制 Docker |
| **Agent 驱动代码生成** | 利用 LEE 的 Agent 能力 | 纯模板生成 |
| **多层验证而非单一检查** | 提高代码质量，降低 LLM 生成失败率 | 单层验证 |
| **错误自动分类** | 减少假失败，提高测试可信度 | 全部人工判断 |

### 8.2 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.10+ |
| 测试框架 | Playwright Python | 1.40+ |
| 断言框架 | pytest | 7.0+ |
| LLM 调用 | lee.llm (内部) | - |
| Docker | docker | 20.10+ (可选) |
| 代码生成 | Jinja2 | 3.1+ |
| AST 解析 | ast (标准库) | - |

### 8.3 参考资源

- [Playwright for Python Documentation](https://playwright.dev/python/)
- [pytest Documentation](https://docs.pytest.org/)
- [Python AST Module](https://docs.python.org/3/library/ast.html)
- [Jinja2 Template Designer](https://jinja.palletsprojects.com/)

---

## 九、评审问题自查

### 9.1 架构合理性

- ✅ 模块职责清晰：Generator 生成、Runner 执行、Validator 验证、Classifier 分类
- ✅ 接口抽象合理：BaseGenerator/BaseRunner 支持扩展
- ✅ 分层明确：L1→L2→L3→L4 验证层次清晰
- ✅ 错误处理完整：自动分类 + 自动修复 + 人工兜底

### 9.2 实现可行性

- ✅ 依赖合理：playwright-python、pytest 都是成熟方案
- ✅ 时间估算合理：6-7天符合模块复杂度
- ✅ 风险可控：主要风险有缓解措施
- ✅ 扩展性预留：支持多框架切换

### 9.3 与现有系统集成

- ✅ 符合现有 L3 工作流模板
- ✅ 契约兼容：test-result/v1/schema.yaml 已定义
- ✅ Agent 对接：script_translator/result_judge 已定义

---

**版本历史**：
- v1.0（初版）：Docker 强制执行
- v1.1（修订）：双模式，简化架构
- v2.0（最终版）：整合质量保证 + 错误分类
- v3.0（当前版）：添加单元测试、系统集成、代码评审环节

**下一步**：
1. 等待评审反馈
2. 根据反馈调整
3. 开始实施
