#!/usr/bin/env python3
"""
DevOps Phase 1 结构验证规则

验证 Phase 1（架构设计）的产物结构、格式和完整性。
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any


def verify(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str = ".") -> Dict[str, Any]:
    """
    执行验证

    Args:
        params: 检查参数
        artifacts: 产物字典
        base_dir: 基础目录

    Returns:
        验证结果字典
    """
    check_type = params.get("check_type")

    if check_type == "file_exists":
        return check_file_exists(params, artifacts, base_dir)
    elif check_type == "yaml_valid":
        return check_yaml_valid(params, artifacts, base_dir)
    elif check_type == "architecture_structure":
        return check_architecture_structure(params, artifacts, base_dir)
    elif check_type == "env_matrix_structure":
        return check_env_matrix_structure(params, artifacts, base_dir)
    elif check_type == "cross_reference":
        return check_cross_reference(params, artifacts, base_dir)
    else:
        return {
            "status": "fail",
            "detail": f"未知的检查类型: {check_type}",
        }


def check_file_exists(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查文件是否存在"""
    required_files = params.get("required_files", [])
    base = Path(base_dir)

    missing_files = []
    for file_path in required_files:
        full_path = base / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        return {
            "status": "fail",
            "detail": f"缺少必需文件: {', '.join(missing_files)}",
            "suggestions": [
                f"请确保以下文件存在: {', '.join(missing_files)}",
            ],
        }

    return {
        "status": "pass",
        "detail": f"所有 {len(required_files)} 个必需文件都存在",
    }


def check_yaml_valid(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查 YAML 文件格式有效性"""
    yaml_files = params.get("yaml_files", [])
    base = Path(base_dir)

    invalid_files = []
    for file_path in yaml_files:
        full_path = base / file_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
        except Exception as e:
            invalid_files.append(f"{file_path}: {str(e)}")

    if invalid_files:
        return {
            "status": "fail",
            "detail": f"YAML 格式无效: {', '.join(invalid_files)}",
            "suggestions": [
                "请检查 YAML 文件格式是否正确",
                "确保使用正确的缩进（空格，不是 Tab）",
                "确保所有字符串正确引用",
            ],
        }

    return {
        "status": "pass",
        "detail": f"所有 {len(yaml_files)} 个 YAML 文件格式正确",
    }


def check_architecture_structure(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查架构文档结构完整性"""
    base = Path(base_dir)
    arch_file = base / "devops/phase1/infra-architecture.yaml"

    try:
        with open(arch_file, 'r', encoding='utf-8') as f:
            arch_content = yaml.safe_load(f)
    except Exception as e:
        return {
            "status": "fail",
            "detail": f"无法读取架构文件: {str(e)}",
        }

    required_sections = params.get("required_sections", [])
    missing_sections = []

    def check_sections(data, sections, prefix=""):
        """递归检查章节"""
        missing = []
        for section in sections:
            if "." in section:
                # 嵌套字段（如 service_topology.app）
                parts = section.split(".")
                current = data
                found = True
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        found = False
                        break
                if not found:
                    missing.append(f"{prefix}{section}")
            else:
                # 顶层字段
                if section not in data:
                    missing.append(f"{prefix}{section}")
                elif isinstance(data[section], dict):
                    # 递归检查嵌套结构
                    pass
        return missing

    missing_sections = check_sections(arch_content, required_sections)

    if missing_sections:
        return {
            "status": "fail",
            "detail": f"架构文档缺少必需章节: {', '.join(missing_sections)}",
            "suggestions": [
                "请补充缺失的章节",
                "参考架构文档模板确保结构完整",
            ],
        }

    return {
        "status": "pass",
        "detail": f"架构文档结构完整，包含所有 {len(required_sections)} 个必需章节",
    }


def check_env_matrix_structure(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查环境矩阵完整性"""
    base = Path(base_dir)
    env_file = base / "devops/phase1/env-matrix.yaml"

    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = yaml.safe_load(f)
    except Exception as e:
        return {
            "status": "fail",
            "detail": f"无法读取环境矩阵文件: {str(e)}",
        }

    # 检查必需环境
    required_environments = params.get("required_environments", [])
    missing_envs = []

    if "environments" not in env_content:
        return {
            "status": "fail",
            "detail": "环境矩阵缺少 environments 字段",
            "suggestions": [
                "请添加 environments 字段",
                "至少需要包含 dev 和 test 环境",
            ],
        }

    for env in required_environments:
        if env not in env_content.get("environments", {}):
            missing_envs.append(env)

    if missing_envs:
        return {
            "status": "fail",
            "detail": f"环境矩阵缺少必需环境: {', '.join(missing_envs)}",
            "suggestions": [
                f"请添加以下环境配置: {', '.join(missing_envs)}",
            ],
        }

    # 检查必需字段
    required_fields = params.get("required_fields", [])
    missing_fields = []

    for field in required_fields:
        if field not in env_content:
            missing_fields.append(field)

    if missing_fields:
        return {
            "status": "fail",
            "detail": f"环境矩阵缺少必需字段: {', '.join(missing_fields)}",
            "suggestions": [
                "请补充缺失的字段",
            ],
        }

    return {
        "status": "pass",
        "detail": f"环境矩阵完整，包含 {len(required_environments)} 个环境和所有必需字段",
    }


def check_cross_reference(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查跨文档引用一致性"""
    base = Path(base_dir)
    references = params.get("references", [])

    inconsistencies = []

    for ref in references:
        source_file = base / ref["source"]
        target_file = base / ref["target"]

        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                source_content = yaml.safe_load(f)
            with open(target_file, 'r', encoding='utf-8') as f:
                target_content = yaml.safe_load(f)
        except Exception as e:
            inconsistencies.append(f"{ref['source']} → {ref['target']}: 读取失败 - {str(e)}")
            continue

        # 获取源字段值
        source_parts = ref["source_field"].split(".")
        source_value = source_content
        for part in source_parts:
            if isinstance(source_value, dict) and part in source_value:
                source_value = source_value[part]
            else:
                break

        # 获取目标字段值
        target_parts = ref["target_field"].split(".")
        target_value = target_content
        for part in target_parts:
            if isinstance(target_value, dict) and part in target_value:
                target_value = target_value[part]
            else:
                break

        # 比较值
        if source_value != target_value:
            inconsistencies.append(
                f"{ref['source']}.{ref['source_field']} ({source_value}) != "
                f"{ref['target']}.{ref['target_field']} ({target_value})"
            )

    if inconsistencies:
        return {
            "status": "warning",  # 跨文档不一致是 warning，不是 error
            "detail": f"发现 {len(inconsistencies)} 处跨文档不一致",
            "suggestions": inconsistencies + [
                "请确保不同文档间的配置保持一致",
            ],
        }

    return {
        "status": "pass",
        "detail": f"所有 {len(references)} 处跨文档引用一致",
    }


# 支持旧接口（check 函数）
def check(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str = ".") -> Dict[str, Any]:
    """检查函数（向后兼容）"""
    return verify(params, artifacts, base_dir)


if __name__ == "__main__":
    # 测试模式
    import json

    test_params = {
        "check_type": "file_exists",
        "required_files": [
            "devops/phase1/infra-architecture.yaml",
            "devops/phase1/env-matrix.yaml",
        ],
    }

    result = verify(test_params, {}, ".")

    print(json.dumps(result, indent=2, ensure_ascii=False))
