"""
Sanitization Utils - 数据脱敏工具

用于在日志和追踪中脱敏敏感信息。
"""

import re
from typing import Any


# 脱敏规则
SANITIZATION_PATTERNS = [
    # Email
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]'),
    # Phone (Chinese)
    (r'1[3-9]\d{9}', '[PHONE]'),
    # API Key patterns
    (r'(sk-|api_key[=:]|token[=:])[a-zA-Z0-9_-]{20,}', '[API_KEY]'),
    # Password
    (r'(password|passwd|pwd)[=:][^\s]+', '[PASSWORD]', re.IGNORECASE),
    # ID Card (Chinese)
    (r'\d{17}[\dXx]', '[ID_CARD]'),
    # Bearer Token
    (r'Bearer [a-zA-Z0-9._-]+', 'Bearer [REDACTED]'),
    # Generic secrets
    (r'(secret|credential|key)[=:][^\s"\']*', r'\1=[REDACTED]', re.IGNORECASE),
]


def sanitize(text: str) -> str:
    """脱敏文本

    Args:
        text: 原始文本

    Returns:
        脱敏后的文本
    """
    if not isinstance(text, str):
        return text

    for pattern in SANITIZATION_PATTERNS:
        if len(pattern) == 3:
            regex, replacement, flags = pattern
            text = re.sub(regex, replacement, text, flags=flags)
        else:
            regex, replacement = pattern
            text = re.sub(regex, replacement, text)

    return text


def sanitize_dict(data: dict) -> dict:
    """脱敏字典中的所有字符串值

    Args:
        data: 原始字典

    Returns:
        脱敏后的字典
    """
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [sanitize_item(v) for v in value]
        else:
            result[key] = value

    return result


def sanitize_item(item: Any) -> Any:
    """脱敏单个值

    Args:
        item: 原始值

    Returns:
        脱敏后的值
    """
    if isinstance(item, str):
        return sanitize(item)
    elif isinstance(item, dict):
        return sanitize_dict(item)
    elif isinstance(item, list):
        return [sanitize_item(v) for v in item]
    else:
        return item
