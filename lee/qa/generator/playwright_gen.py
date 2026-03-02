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
    Playwright TypeScript code generator.

    Generates @playwright/test TypeScript test code from test cases.
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
        return """你是一个 Playwright TypeScript 测试代码生成专家。

# 代码规范

1. 使用 @playwright/test 框架
2. 使用 TypeScript
3. 每个测试用例一个独立的 test 函数
4. 使用 data-testid 选择器（优先级最高）
5. 包含适当的错误处理
6. 使用 expect() 进行断言
7. 添加清晰的 docstring

# 代码结构

```typescript
import { test, expect } from '@playwright/test';

test.describe('测试套件名称', () => {
  test('用例名称', async ({ page }) => {
    // 测试代码
  });
});
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
- 避免使用 page.waitForTimeout()

# 断言模式

- expect(locator).toBeVisible()
- expect(page).toHaveURL('...')
- expect(page).toHaveTitle('...')
"""

    def _build_user_prompt(self, request: GenerationRequest) -> str:
        """Build user prompt from request"""
        prompt = f"""
# 测试任务

请根据以下测试用例生成 Playwright TypeScript 测试代码：

## 测试环境
- Base URL: {request.base_url}
- 框架: @playwright/test (TypeScript)
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

请生成完整的 TypeScript 测试代码，包括：
1. 所有必要的 import 语句 (from '@playwright/test')
2. test.describe() 测试套件
3. 所有测试函数 (test())
4. 适当的 beforeEach/afterEach

只返回代码，不要有其他解释。
"""
        return prompt

    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response"""
        # Remove markdown code blocks
        if "```typescript" in response:
            parts = response.split("```typescript")
            if len(parts) > 1:
                code = parts[1].split("```")[0].strip()
                return code
        elif "```ts" in response:
            parts = response.split("```ts")
            if len(parts) > 1:
                code = parts[1].split("```")[0].strip()
                return code
        elif "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                code = parts[1].strip()
                # Remove language identifier if present
                if code.startswith("typescript") or code.startswith("ts"):
                    code = code[code.index("\n") + 1:].strip()
                return code

        return response.strip()

    def _load_templates(self):
        """Load Jinja2 templates"""
        # Templates can be loaded from files or defined inline
        self.template = Template(self._get_base_template())

    def _get_base_template(self) -> str:
        """Get base code template"""
        return """import { test, expect } from '@playwright/test';

test.describe('Test Suite', () => {
{% for test in tests %}
  test('{{ test.name }}', async ({ page }) => {
    // {{ test.title }}
    // Expected: {{ test.expected }}
    {{ test.code }}
  });
{% endfor %}
});
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

    def _split_into_files(self, code: str, request: GenerationRequest) -> Dict[str, str]:
        """Split code into multiple files including config files"""
        return {
            "package.json": self._get_package_json(),
            "playwright.config.ts": self._get_playwright_config(request.base_url),
            "tsconfig.json": self._get_tsconfig(),
            "e2e/test.spec.ts": code,
        }

    def _get_package_json(self) -> str:
        """Get package.json content"""
        import json
        return json.dumps({
            "name": "e2e-tests",
            "version": "1.0.0",
            "description": "Generated E2E tests",
            "scripts": {
                "test": "playwright test",
                "test:headed": "playwright test --headed",
                "test:ui": "playwright test --ui"
            },
            "devDependencies": {
                "@playwright/test": "^1.42.0",
                "typescript": "^5.0.0"
            }
        }, indent=2)

    def _get_playwright_config(self, base_url: str) -> str:
        """Get playwright.config.ts content"""
        return f"""import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {{
    baseURL: '{base_url}',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  }},
  projects: [
    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
  ],
}});
"""

    def _get_tsconfig(self) -> str:
        """Get tsconfig.json content"""
        import json
        return json.dumps({
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "lib": ["ES2020"],
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "moduleResolution": "node",
                "resolveJsonModule": True,
                "types": ["@playwright/test"]
            },
            "include": ["e2e/**/*"],
            "exclude": ["node_modules"]
        }, indent=2)
