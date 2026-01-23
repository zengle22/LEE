"""
Demo 模块 - 简单的加法函数
"""


def add(a: int, b: int) -> int:
    """
    返回两个整数的和。

    Args:
        a: 第一个整数
        b: 第二个整数

    Returns:
        两个整数的和
    """
    return a + b


if __name__ == "__main__":
    # 简单测试
    print(f"2 + 3 = {add(2, 3)}")
    print(f"5 + (-3) = {add(5, -3)}")
