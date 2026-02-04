"""
Test full file write process
"""
import asyncio
import sys
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.execution.file_output_handler import FileOutputHandler
from lee.orchestrator.storage.models import OutputSpec


async def test_full_write():
    project_root = Path("e:/projects/ai-marathon-coach").resolve()

    # 模拟 LLM 输出
    llm_output = """
你是 DevOps 实施工程师。请基于项目配置生成以下 8 个文件。

**重要**：
- 不要生成 devops/infra-architecture.yaml、devops/env-matrix.yaml、devops/release-strategy.md（这些已由 p1_architecture 生成）

必须生成的文件（按顺序输出）：

## devops/infra/docker-compose.yml
```yaml
services:
  backend:
    image: ${PROJECT_NAME}-backend:latest
    ports:
      - "8080:8080"
```

## devops/infra/ansible/inventory/dev.yml
```ini
[dev_servers]
dev1 ansible_host=localhost ansible_user=deploy
```
"""

    handler = FileOutputHandler()

    # 模拟输出规格
    outputs = [
        OutputSpec(type="dir", path="devops/infra", format="yaml", required=True, description="Infrastructure code"),
        OutputSpec(type="dir", path="devops/cicd", format="yaml", required=True, description="CI/CD config"),
        OutputSpec(type="dir", path="devops/scripts", format="text", required=True, description="Deployment scripts"),
    ]

    # 写入文件
    written_files = await handler.write_output(
        llm_output=llm_output,
        output_specs=outputs,
        project_root=str(project_root)
    )

    print(f"✅ 写入了 {len(written_files)} 个文件:")
    for f in written_files:
        print(f"   {f}")


if __name__ == "__main__":
    asyncio.run(test_full_write())
