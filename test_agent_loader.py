"""
Test agent spec loading
"""
import sys
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.execution.agent_loader import AgentLoader

# 设置路径
project_root = Path("e:/projects/ai-marathon-coach").resolve()
lee_root = Path("E:/ai/LEE").resolve()
spec_root = lee_root / "spec-global"

print(f"项目根目录: {project_root}")
print(f"LEE根目录: {lee_root}")
print(f"Spec根目录: {spec_root}")

# 创建 AgentLoader
loader = AgentLoader(project_root=str(project_root), spec_root=str(spec_root))

# 测试加载 agent spec
agent_refs = [
    "agent.devops.architect",
    "agent.devops.implementation",
    "agent.devops.verification",
]

for agent_ref in agent_refs:
    print(f"\n🔍 加载 Agent: {agent_ref}")
    try:
        spec = loader.load(agent_ref)
        if spec:
            print(f"   ✅ 成功加载")
            print(f"      ID: {spec.id}")
            print(f"      名称: {spec.name}")
            print(f"      部门: {spec.department}")
        else:
            print(f"   ❌ 加载失败 (返回 None)")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
