"""
Test FileOutputHandler filename extraction
"""
import sys
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.execution.file_output_handler import FileOutputHandler


def test_extraction():
    # 模拟 LLM 输出（使用 user_prompt_template 中的格式）
    llm_output = """
## devops/infra/docker-compose.yml
```yaml
services:
  backend:
    image: ${PROJECT_NAME}-backend:latest
```

## devops/infra/ansible/inventory/dev.yml
```ini
[dev_servers]
dev1 ansible_host=localhost ansible_user=deploy
```

## devops/infra/ansible/playbooks/setup-environment.yml
```yaml
---
- name: Setup Docker environment
  hosts: all
  tasks:
    - name: Install Docker
      apt:
        name: docker.io
        state: present
```
"""

    handler = FileOutputHandler()
    parsed = handler._parse_llm_output(llm_output)

    print(f"📊 解析结果 ({len(parsed)} 个文件):")
    for p in parsed:
        print(f"   filename: {p.filename}")
        print(f"   format: {p.format}")
        print(f"   content (前100字符): {p.content[:100]}...")
        print()


if __name__ == "__main__":
    test_extraction()
