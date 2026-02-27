"""
QA Module - Playwright Generator

Playwright-specific code generator implementation.
"""

from typing import Dict, Any
from jinja2 import Template

from lee.qa.generator.base import BaseGenerator, GenerationRequest, GenerationResult
from lee.qa.utils.llm import LLMClient


class PlaywrightGenerator(BaseGenerator):
    """
    Playwright Python code generator.

    Generates pytest-based Playwright test code from test cases.
    """

    def __init__(self, llm_client: LLMClient = None):
        """
        Initialize generator.

        Args:
            llm_client: Optional LLM client for code generation
        """
        super().__init__()
        self.llm = llm_client or LLMClient()
        self._load_templates()

    @property
    def name(self) -> str:
        return "playwright"

    @property
    def framework(self) -> str:
        return "playwright"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate Playwright test code.

        Args:
            request: Generation request with test cases

        Returns:
            GenerationResult with generated code
        """
        return self._validate_and_retry(request)

    def _llm_generate(self, request: GenerationRequest) -> str:
        """
        Call LLM to generate code.

        Args:
            request: Generation request

        Returns:
            Generated code string
        """
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_user_prompt(request)

        response = self.llm.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=4000,
        )

        return self._extract_code(response)

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM"""
        return """你是一个 Playwright 测试代码生成专家。

# 代码规范

1. 使用 playwright.sync_api
2. 使用 pytest 框架
3. 每个测试用例一个独立的 test 函数
4. 使用 data-testid 选择器（优先级最高）
5. 包含适当的错误处理
6. 使用 expect() 进行断言
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
- 避免使用 page.wait_for_timeout()

# 断言模式

- expect(page.locator()).to_be_visible()
- expect(page).to_have_url("...")
- expect(page).to_have_title("...")
"""

    def _build_user_prompt(self, request: GenerationRequest) -> str:
        """Build user prompt from request"""
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
### 用例 {i}: {tc.get('case_id', f'case_{i}')}
- **标题**: {tc.get('title', 'N/A')}
- **优先级**: {tc.get('priority', 'N/A')}
- **类型**: {tc.get('type', 'N/A')}
"""
            if tc.get('preconditions'):
                prompt += f"\n**前置条件**:\n"
                for pre in tc.get('preconditions', []):
                    prompt += f"- {pre}\n"

            if tc.get('steps'):
                prompt += f"\n**测试步骤**:\n"
                for step in tc.get('steps', []):
                    action = step.get('action', '')
                    expected = step.get('expected', '')
                    prompt += f"{step.get('step_num', '?')}. {action}\n   预期: {expected}\n"

            prompt += f"\n**预期结果**: {tc.get('expected_result', 'N/A')}\n"

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
        """Extract code from LLM response"""
        # Remove markdown code blocks
        if "```python" in response:
            parts = response.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0].strip()
                return code
        elif "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                code = parts[1].strip()
                # Remove language identifier if present
                if code.startswith("python"):
                    code = code[6:].strip()
                return code

        return response.strip()

    def _load_templates(self):
        """Load Jinja2 templates"""
        # Templates can be loaded from files or defined inline
        self.template = Template(self._get_base_template())

    def _get_base_template(self) -> str:
        """Get base code template"""
        return """import pytest
import os
from playwright.sync_api import sync_playwright, expect

@pytest.fixture(scope="module")
def browser_context():
    \"\"\"Browser context fixture\"\"\"
    base_url = os.getenv("BASE_URL", "{{ base_url }}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(base_url=base_url)
        page = context.new_page()
        yield page
        browser.close()

{% for test in tests %}
def test_{{ test.name }}(page):
    \"\"\"
    {{ test.title }}

    {% if test.steps %}
    步骤:
    {% for step in test.steps %}
    - {{ step }}
    {% endfor %}
    {% endif %}

    预期: {{ test.expected }}
    \"\"\"
    {{ test.code }}
{% endfor %}
"""

    def _retry_with_schema_feedback(
        self,
        request: GenerationRequest,
        code: str,
        errors: list
    ) -> str:
        """Retry with schema validation feedback"""
        feedback = self._build_feedback_prompt(code, errors, "schema")
        return self.llm.complete_with_feedback(
            original_prompt=self._build_user_prompt(request),
            feedback=feedback,
        )

    def _retry_with_syntax_feedback(
        self,
        request: GenerationRequest,
        code: str,
        errors: list
    ) -> str:
        """Retry with syntax validation feedback"""
        feedback = self._build_feedback_prompt(code, errors, "syntax")
        return self.llm.complete_with_feedback(
            original_prompt=self._build_user_prompt(request),
            feedback=feedback,
        )

    def _split_into_files(self, code: str) -> Dict[str, str]:
        """Split code into multiple files"""
        # For now, return single file
        # Future: split into test_*.py files per function
        return {
            "test_main.py": code,
            "conftest.py": self._get_conftest(),
        }

    def _get_conftest(self) -> str:
        """Get conftest.py content"""
        return """import pytest

@pytest.fixture(scope="session")
def base_url():
    import os
    return os.getenv("BASE_URL", "http://localhost:3000")
"""
