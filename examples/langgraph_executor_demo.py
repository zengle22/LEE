#!/usr/bin/env python3
"""
LangGraph Executor 演示脚本

演示如何使用 LangGraph Executor 执行代码实现和单元测试任务。

使用方式:
    # 运行所有演示
    python examples/langgraph_executor_demo.py

    # 只运行特定演示
    python examples/langgraph_executor_demo.py --demo impl
    python examples/langgraph_executor_demo.py --demo test
    python examples/langgraph_executor_demo.py --demo orchestrator
"""

import os
import sys
import tempfile
import argparse
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title: str):
    """打印小节标题"""
    print(f"\n--- {title} ---")


# ============================================================
# Demo 1: 直接使用 run_task() 执行代码实现
# ============================================================

def demo_impl_coding():
    """演示代码实现任务"""
    print_header("Demo 1: 代码实现任务 (l3.impl.coding)")

    from lee.runtime.executor import run_task, ExecutorTaskSpec, TaskStatus
    from lee.runtime.executor.profiles.loader import list_profiles

    # 显示可用的 LLM Profiles
    print_section("可用的 LLM Profiles")
    profiles = list_profiles()
    for p in profiles:
        print(f"  - {p}")

    # 选择 Profile（优先使用 zhipu）
    profile = "zhipu" if "zhipu" in profiles else profiles[0]
    print(f"\n使用 Profile: {profile}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建设计文档
        print_section("创建设计文档")
        design_path = os.path.join(tmpdir, "design.md")
        design_content = """
# Calculator 模块设计

## 功能需求
实现一个简单的计算器模块，包含基本的数学运算。

## 接口定义

```python
def add(a: float, b: float) -> float:
    '''两数相加'''
    pass

def subtract(a: float, b: float) -> float:
    '''两数相减'''
    pass

def multiply(a: float, b: float) -> float:
    '''两数相乘'''
    pass

def divide(a: float, b: float) -> float:
    '''两数相除，除数为0时抛出 ValueError'''
    pass
```

## 输出格式要求
使用以下格式输出代码：
===FILE:calculator.py===
<代码内容>
===END===
"""
        with open(design_path, "w") as f:
            f.write(design_content)
        print(f"  设计文档: {design_path}")

        # 创建任务规格
        print_section("创建任务规格")
        task = ExecutorTaskSpec(
            task_id="demo-calc-impl",
            task_type="l3.impl.coding",
            inputs={
                "design_spec": design_path,
                "repo_workspace": tmpdir,
            },
            llm_profile=profile,
            llm_max_tokens=1000,
        )
        print(f"  Task ID: {task.task_id}")
        print(f"  Task Type: {task.task_type}")
        print(f"  LLM Profile: {task.llm_profile}")

        # 执行任务
        print_section("执行任务")
        print("  正在调用 LLM 生成代码...")
        result = run_task(task)

        # 显示结果
        print_section("执行结果")
        print(f"  状态: {result.status.value}")
        print(f"  消息: {result.message}")
        print(f"  Token 消耗: {result.tokens_used}")

        print_section("执行日志")
        for log in result.logs:
            print(f"  {log}")

        # 显示生成的文件
        print_section("生成的文件")
        for f in os.listdir(tmpdir):
            if f.endswith('.py') or f.endswith('.md'):
                fpath = os.path.join(tmpdir, f)
                if os.path.isfile(fpath):
                    print(f"\n  📄 {f}:")
                    print("  " + "-" * 40)
                    with open(fpath) as file:
                        for line in file:
                            print(f"  {line.rstrip()}")

        return result.status == TaskStatus.SUCCESS


# ============================================================
# Demo 2: 使用 run_task() 执行单元测试
# ============================================================

def demo_unit_test():
    """演示单元测试任务"""
    print_header("Demo 2: 单元测试任务 (l3.test.unit)")

    from lee.runtime.executor import run_task, ExecutorTaskSpec, TaskStatus

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        print_section("创建测试文件")

        test_file = os.path.join(tmpdir, "test_sample.py")
        test_content = '''
def test_addition():
    """测试加法"""
    assert 1 + 1 == 2

def test_string():
    """测试字符串"""
    assert "hello".upper() == "HELLO"

def test_list():
    """测试列表"""
    items = [1, 2, 3]
    assert len(items) == 3
    assert sum(items) == 6
'''
        with open(test_file, "w") as f:
            f.write(test_content)
        print(f"  测试文件: {test_file}")

        # 创建任务规格
        print_section("创建任务规格")
        task = ExecutorTaskSpec(
            task_id="demo-unit-test",
            task_type="l3.test.unit",
            inputs={
                "repo_workspace": tmpdir,
            },
            params={
                "test_framework": "pytest",
                "test_patterns": ["test_sample.py"],
            },
        )
        print(f"  Task ID: {task.task_id}")
        print(f"  Task Type: {task.task_type}")

        # 执行任务
        print_section("执行任务")
        result = run_task(task)

        # 显示结果
        print_section("执行结果")
        print(f"  状态: {result.status.value}")
        print(f"  消息: {result.message}")

        print_section("执行日志")
        for log in result.logs:
            print(f"  {log}")

        if result.metrics:
            print_section("测试指标")
            for key, value in result.metrics.items():
                print(f"  {key}: {value}")

        return result.status == TaskStatus.SUCCESS


# ============================================================
# Demo 3: 通过 Orchestrator ExecutorFactory 使用
# ============================================================

def demo_orchestrator_integration():
    """演示通过 Orchestrator 集成使用"""
    print_header("Demo 3: Orchestrator 集成 (ExecutorFactory)")

    from lee.orchestrator.execution import ExecutorFactory, LangGraphExecutor

    # 显示已注册的执行器
    print_section("已注册的执行器类型")
    for name, cls in ExecutorFactory._executors.items():
        print(f"  - {name}: {cls.__name__ if cls else 'None'}")

    # 创建 LangGraph 执行器
    print_section("创建 LangGraph 执行器")
    executor = ExecutorFactory.create(
        "langgraph",
        default_profile="zhipu",
    )
    print(f"  执行器类型: {type(executor).__name__}")
    print(f"  默认 Profile: {executor.default_profile}")

    # 异步执行示例
    async def run_async_demo():
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建简单的设计文档
            design_path = os.path.join(tmpdir, "design.md")
            with open(design_path, "w") as f:
                f.write("""
# Hello Module

Create a simple hello function.

Output format:
===FILE:hello.py===
def hello(name):
    return f"Hello, {name}!"
===END===
""")

            print_section("执行任务 (async)")
            result = await executor.execute({
                "task_type": "l3.impl.coding",
                "task_id": "demo-orchestrator",
                "inputs": {
                    "design_spec": design_path,
                    "repo_workspace": tmpdir,
                },
                "llm_max_tokens": 500,
            })

            print_section("执行结果")
            print(f"  状态: {result['status']}")
            print(f"  消息: {result.get('message', 'N/A')}")
            print(f"  Token 消耗: {result.get('tokens_used', 0)}")

            # 显示生成的文件
            py_files = [f for f in os.listdir(tmpdir) if f.endswith('.py')]
            if py_files:
                print_section("生成的文件")
                for f in py_files:
                    fpath = os.path.join(tmpdir, f)
                    print(f"\n  📄 {f}:")
                    with open(fpath) as file:
                        for line in file:
                            print(f"    {line.rstrip()}")

            return result['status'] == 'success'

    return asyncio.run(run_async_demo())


# ============================================================
# Demo 4: 查看系统信息
# ============================================================

def demo_system_info():
    """显示系统信息"""
    print_header("系统信息")

    from lee.runtime.executor import list_registered_types
    from lee.runtime.executor.profiles.loader import list_profiles, load_profile

    print_section("已注册的任务类型 (Graph Builders)")
    for task_type in list_registered_types():
        print(f"  - {task_type}")

    print_section("可用的 LLM Profiles")
    for profile_name in list_profiles():
        try:
            profile = load_profile(profile_name)
            print(f"  - {profile_name}:")
            print(f"      Provider: {profile.provider}")
            print(f"      Model: {profile.model}")
            print(f"      API Key: {'✓ 已配置' if profile.api_key else '✗ 未配置'}")
        except ValueError as e:
            print(f"  - {profile_name}: ✗ {e}")

    return True


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="LangGraph Executor 演示脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
演示类型:
  info         显示系统信息
  impl         代码实现任务演示 (需要 LLM API)
  test         单元测试任务演示
  orchestrator Orchestrator 集成演示 (需要 LLM API)
  all          运行所有演示
""")
    parser.add_argument(
        "--demo",
        choices=["info", "impl", "test", "orchestrator", "all"],
        default="info",
        help="要运行的演示类型 (默认: info)"
    )
    args = parser.parse_args()

    demos = {
        "info": ("系统信息", demo_system_info),
        "impl": ("代码实现", demo_impl_coding),
        "test": ("单元测试", demo_unit_test),
        "orchestrator": ("Orchestrator 集成", demo_orchestrator_integration),
    }

    results = {}

    if args.demo == "all":
        for name, (title, func) in demos.items():
            try:
                results[name] = func()
            except Exception as e:
                print(f"\n❌ {title} 演示失败: {e}")
                results[name] = False
    else:
        name = args.demo
        title, func = demos[name]
        try:
            results[name] = func()
        except Exception as e:
            print(f"\n❌ {title} 演示失败: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # 打印总结
    print_header("演示总结")
    for name, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {demos[name][0]}: {status}")


if __name__ == "__main__":
    main()
