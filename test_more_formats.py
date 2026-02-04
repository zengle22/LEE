"""
Test more LLM output formats
"""
import re


def test_formats():
    # 可能的LLM输出格式

    # 格式1: 基本格式（应该匹配）
    text1 = """## devops/infra/docker-compose.yml
```yaml
services:
  backend:
    image: test
```
"""

    # 格式2: 有描述文本的格式
    text2 = """## devops/infra/docker-compose.yml
This is the docker compose file.

```yaml
services:
  backend:
    image: test
```
"""

    # 格式3: 使用中文序号的格式
    text3 = """1. ## devops/infra/docker-compose.yml
```yaml
services:
  backend:
    image: test
```
"""

    # 格式4: 用户实际使用的格式（来自 user_prompt_template）
    text4 = """必须是以下 8 个文件：

## devops/infra/docker-compose.yml
```yaml
services:
  backend:
    image: test
```
"""

    # 正则表达式
    pattern = r"^(#{1,6})\s*([^\n#]+?)\s*\n\s*```(yaml|yml|json|markdown|md|text|bash|sh|shell)(?:\n?[^\n]*)?\n(.*?)```"

    test_cases = [
        ("基本格式", text1),
        ("有描述文本", text2),
        ("中文序号", text3),
        ("用户实际格式", text4),
    ]

    for name, text in test_cases:
        print(f"\n--- {name} ---")
        matches = list(re.finditer(pattern, text, re.MULTILINE | re.DOTALL))
        print(f"匹配数: {len(matches)}")
        if matches:
            for match in matches:
                heading_text = match.group(2).strip()
                print(f"   提取的文件名: {heading_text}")
        else:
            print(f"   ❌ 没有匹配")
            # 显示前200个字符用于调试
            print(f"   文本内容: {text[:200]}")


if __name__ == "__main__":
    test_formats()
