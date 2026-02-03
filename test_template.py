"""
Test template loading and step parsing
"""
import sys
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.execution.template_manager import TemplateManager

# 设置路径
lee_root = Path("E:/ai/LEE").resolve()
template_dir = lee_root / "spec-global" / "departments" / "devops" / "workflows"

print(f"模板目录: {template_dir}")
print(f"模板目录存在: {template_dir.exists()}")

# 创建模板管理器
tm = TemplateManager(template_dir=str(template_dir))

# 加载所有模板
templates = tm.load_all_templates()
print(f"\n✅ 加载了 {len(templates)} 个模板:")
for tid, template in templates.items():
    print(f"   {tid}:")
    print(f"      名称: {template.name}")
    print(f"      层级: {template.level}")
    print(f"      步骤数: {len(template.steps)}")
    for step in template.steps:
        print(f"         - {step.id} ({step.kind}): {step.name}")
    print(f"      完成: {template.completion_criteria}")

# 获取特定模板的步骤
template_id = "workflow.devops.deployment"
print(f"\n📋 获取模板 '{template_id}' 的步骤:")
steps = tm.get_steps(template_id)
print(f"   步骤数: {len(steps)}")
for step in steps:
    print(f"   - {step.id} ({step.kind}): {step.name}")
    if hasattr(step, 'agent'):
        print(f"      Agent: {step.agent}")
