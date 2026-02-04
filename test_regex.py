"""
Test regex pattern for file extraction
"""
import re


def test_regex():
    # 测试不同的输入格式

    # 格式1: user_prompt_template 中的格式
    text1 = """## devops/infra/docker-compose.yml
```yaml
services:
  backend:
    image: ${PROJECT_NAME}-backend:latest
```
"""

    # 格式2: 没有换行的格式
    text2 = """## devops/infra/docker-compose.yml
```yaml
services:
  backend:
    image: ${PROJECT_NAME}-backend:latest
```
"""

    # 格式3: 有空行的格式
    text3 = """## devops/infra/docker-compose.yml

```yaml
services:
  backend:
    image: ${PROJECT_NAME}-backend:latest
```
"""

    # 正则表达式（来自代码）
    pattern = r"^(#{1,6})\s*([^\n#]+?)\s*\n\s*```(yaml|yml|json|markdown|md|text|bash|sh|shell)(?:\n?[^\n]*)?\n(.*?)```"

    for i, text in enumerate([text1, text2, text3], 1):
        print(f"\n--- 测试格式 {i} ---")
        matches = list(re.finditer(pattern, text, re.MULTILINE | re.DOTALL))
        print(f"匹配数: {len(matches)}")
        for match in matches:
            heading_text = match.group(2).strip()
            lang = match.group(3)
            content = match.group(4).strip()[:50]
            print(f"   提取的文件名: {heading_text}")
            print(f"   语言: {lang}")
            print(f"   内容: {content}...")


if __name__ == "__main__":
    test_regex()
