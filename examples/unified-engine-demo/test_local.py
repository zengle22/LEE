#!/usr/bin/env python3
"""
测试本地 OpenAI 兼容服务

使用本地服务器 (http://127.0.0.1:8045/v1) 测试统一 Engine 接口
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flowcore.orchestrator.cli import main


if __name__ == "__main__":
    # 模拟命令行参数
    sys.argv = [
        "orchestrator",
        "run-engine",
        str(Path(__file__).parent),  # project_dir
        "step1_test_local"  # step_id
    ]

    sys.exit(main())
