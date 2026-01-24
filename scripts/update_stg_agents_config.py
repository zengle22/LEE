#!/usr/bin/env python3
"""
批量更新 STG Agents 的 LLM 配置
将所有 agent spec 的 engine 配置更新为使用本地反代
"""

import os
import sys
from pathlib import Path
import yaml

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
STG_AGENTS_DIR = PROJECT_ROOT / "spec-global" / "departments" / "stg" / "agents"

# 本地反代配置
LOCAL_ENGINE_CONFIG = """
engine:
  type: llm
  provider: custom
  base_url: http://127.0.0.1:8045/v1
  api_key: sk-2988e892730744ccafde80aac9ced361
  model: gemini-3-flash
  temperature: 0.7
  max_tokens: 4000
"""


def update_agent_engine(agent_yaml_path: Path) -> bool:
    """更新单个 agent 的 engine 配置"""
    try:
        with open(agent_yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已经有正确的配置
        if '127.0.0.1:8045' in content:
            return False  # 已经是正确的配置，跳过

        # 解析 YAML
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            return False

        # 更新 engine 配置
        data['engine'] = {
            'type': 'llm',
            'provider': 'custom',
            'base_url': 'http://127.0.0.1:8045/v1',
            'api_key': 'sk-2988e892730744ccafde80aac9ced361',
            'model': 'gemini-3-flash',
            'temperature': 0.7,
            'max_tokens': 4000
        }

        # 写回文件
        with open(agent_yaml_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

        return True

    except Exception as e:
        print(f"❌ 更新失败 {agent_yaml_path.name}: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("  批量更新 STG Agents LLM 配置")
    print("=" * 70)

    if not STG_AGENTS_DIR.exists():
        print(f"❌ 目录不存在: {STG_AGENTS_DIR}")
        return 1

    # 查找所有 agent.yaml 文件
    agent_files = list(STG_AGENTS_DIR.glob("*/v1/agent.yaml"))

    if not agent_files:
        print(f"⚠️  未找到 agent.yaml 文件")
        return 1

    print(f"\n📁 找到 {len(agent_files)} 个 agent 文件")
    print(f"\n🔧 开始更新...")

    updated_count = 0
    skipped_count = 0

    for agent_file in agent_files:
        agent_name = agent_file.parent.parent.name  # 获取 agent 目录名

        if update_agent_engine(agent_file):
            print(f"  ✅ {agent_name}")
            updated_count += 1
        else:
            print(f"  ⏭️  {agent_name} (已是正确配置或非 agent 文件)")
            skipped_count += 1

    print(f"\n" + "=" * 70)
    print(f"✅ 更新完成！")
    print(f"   更新: {updated_count} 个")
    print(f"   跳过: {skipped_count} 个")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
