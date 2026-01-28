#!/usr/bin/env python3
"""
DevOps Phase 2 结构验证规则

验证 Phase 2（基础设施与 CI/CD 实现）的产物结构、格式和质量。
"""

import os
import re
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
    elif check_type == "script_executable":
        return check_script_executable(params, artifacts, base_dir)
    elif check_type == "docker_compose_valid":
        return check_docker_compose_valid(params, artifacts, base_dir)
    elif check_type == "security_practices":
        return check_security_practices(params, artifacts, base_dir)
    elif check_type == "deploy_script_structure":
        return check_deploy_script_structure(params, artifacts, base_dir)
    elif check_type == "placeholder_consistency":
        return check_placeholder_consistency(params, artifacts, base_dir)
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


def check_script_executable(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查 Shell 脚本可执行性"""
    scripts = params.get("scripts", [])
    base = Path(base_dir)

    issues = []

    for script_path in scripts:
        full_path = base / script_path

        # 检查文件是否存在
        if not full_path.exists():
            issues.append(f"{script_path}: 文件不存在")
            continue

        # 检查执行权限
        if not os.access(full_path, os.X_OK):
            issues.append(f"{script_path}: 缺少执行权限")

        # 检查 Shebang
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line.startswith("#!"):
                    issues.append(f"{script_path}: 缺少 Shebang (#!/bin/bash 或 #!/usr/bin/env bash)")
        except Exception as e:
            issues.append(f"{script_path}: 读取失败 - {str(e)}")

        # 基本语法检查（检查常见错误）
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # 检查是否有 set -e
                if "set -e" not in content:
                    issues.append(f"{script_path}: 建议添加 'set -e' 以在错误时退出")

                # 检查是否有函数定义
                if "function " not in content and "() {" not in content:
                    issues.append(f"{script_path}: 建议使用函数组织代码")

        except Exception:
            pass

    if issues:
        return {
            "status": "fail",
            "detail": f"脚本检查发现问题: {len(issues)} 个",
            "suggestions": issues,
        }

    return {
        "status": "pass",
        "detail": f"所有 {len(scripts)} 个脚本可执行",
    }


def check_docker_compose_valid(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查 Docker Compose 配置有效性"""
    base = Path(base_dir)
    compose_file = base / params.get("compose_file", "devops/phase2/docker-compose.yml")

    try:
        with open(compose_file, 'r', encoding='utf-8') as f:
            compose_content = yaml.safe_load(f)
    except Exception as e:
        return {
            "status": "fail",
            "detail": f"无法解析 Docker Compose 文件: {str(e)}",
            "suggestions": [
                "请检查 YAML 格式是否正确",
                "确保缩进使用空格而不是 Tab",
            ],
        }

    issues = []

    # 检查版本
    if "version" not in compose_content:
        issues.append("缺少 version 字段")

    # 检查必需的服务
    required_services = params.get("required_services", [])
    if "services" not in compose_content:
        issues.append("缺少 services 字段")
    else:
        services = compose_content["services"]
        for service in required_services:
            if service not in services:
                issues.append(f"缺少必需服务: {service}")

    # 检查必需的顶级字段
    required_sections = params.get("required_sections", [])
    for section in required_sections:
        if section not in compose_content:
            issues.append(f"缺少 {section} 字段")

    # 检查服务健康检查
    if "services" in compose_content:
        services_no_health = []
        for service_name, service_config in compose_content["services"].items():
            if "healthcheck" not in service_config:
                services_no_health.append(service_name)

        if services_no_health:
            issues.append(f"以下服务缺少健康检查: {', '.join(services_no_health)}")

    if issues:
        return {
            "status": "fail",
            "detail": f"Docker Compose 配置发现问题: {len(issues)} 个",
            "suggestions": issues,
        }

    return {
        "status": "pass",
        "detail": f"Docker Compose 配置有效，包含 {len(compose_content.get('services', {}))} 个服务",
    }


def check_security_practices(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查安全最佳实践"""
    base = Path(base_dir)
    checks = params.get("checks", {})
    issues = []

    # 检查硬编码密钥
    if "no_hardcoded_secrets" in checks:
        check_config = checks["no_hardcoded_secrets"]
        files_to_check = check_config.get("files", [])
        patterns = check_config.get("patterns", [])
        allowed_placeholders = check_config.get("allowed_placeholders", [])

        for file_pattern in files_to_check:
            file_path = base / file_pattern
            if not file_path.exists():
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                    for i, line in enumerate(lines, 1):
                        for pattern in patterns:
                            if pattern in line:
                                # 检查是否是允许的占位符
                                is_placeholder = any(ph in line for ph in allowed_placeholders)
                                if not is_placeholder:
                                    issues.append(f"{file_pattern}:{i}: 可能包含硬编码的 {pattern}")

            except Exception:
                pass

    # 检查健康检查
    if "health_checks_enabled" in checks:
        check_config = checks["health_checks_enabled"]
        compose_file = base / check_config.get("compose_file", "devops/phase2/docker-compose.yml")

        try:
            with open(compose_file, 'r', encoding='utf-8') as f:
                compose_content = yaml.safe_load(f)

            if "services" in compose_content:
                require_all = check_config.get("require_all", False)
                services_no_health = []

                for service_name, service_config in compose_content["services"].items():
                    if "healthcheck" not in service_config:
                        if require_all:
                            services_no_health.append(service_name)

                if services_no_health:
                    issues.append(f"以下服务缺少健康检查: {', '.join(services_no_health)}")

        except Exception:
            pass

    # 检查回滚脚本
    if "rollback_exists" in checks:
        check_config = checks["rollback_exists"]
        rollback_file = base / check_config.get("file", "devops/phase2/deploy/rollback-dev-test.sh")

        if not rollback_file.exists():
            issues.append(f"缺少回滚脚本: {check_config.get('file')}")

    if issues:
        return {
            "status": "fail",
            "detail": f"安全检查发现问题: {len(issues)} 个",
            "suggestions": issues,
        }

    return {
        "status": "pass",
        "detail": "安全最佳实践检查通过",
    }


def check_deploy_script_structure(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查部署脚本完整性"""
    base = Path(base_dir)
    script_file = base / params.get("script_file", "devops/phase2/deploy/deploy-dev-test.sh")

    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {
            "status": "fail",
            "detail": f"无法读取部署脚本: {str(e)}",
        }

    issues = []
    missing_functions = []

    # 检查必需函数
    required_functions = params.get("required_functions", [])
    for func in required_functions:
        # 检查函数定义（支持两种语法：function name 和 name()）
        if f"function {func}" not in content and f"{func}()" not in content:
            missing_functions.append(func)

    if missing_functions:
        issues.append(f"缺少必需函数: {', '.join(missing_functions)}")

    # 检查错误处理
    required_error_handling = params.get("required_error_handling", [])
    missing_error_handling = []

    for eh in required_error_handling:
        if eh not in content:
            missing_error_handling.append(eh)

    if missing_error_handling:
        issues.append(f"缺少错误处理: {', '.join(missing_error_handling)}")

    if issues:
        return {
            "status": "fail",
            "detail": f"部署脚本结构不完整: {len(issues)} 个问题",
            "suggestions": issues,
        }

    return {
        "status": "pass",
        "detail": "部署脚本结构完整，包含所有必需函数和错误处理",
    }


def check_placeholder_consistency(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> Dict[str, Any]:
    """检查环境变量占位符一致性"""
    base = Path(base_dir)
    reference_file = base / params.get("reference_file", "devops/phase1/env-matrix.yaml")
    target_files = params.get("target_files", [])

    try:
        # 从参考文件提取环境变量
        with open(reference_file, 'r', encoding='utf-8') as f:
            ref_content = yaml.safe_load(f)

        # 提取所有占位符（${VAR_NAME} 格式）
        ref_vars = set()
        def extract_placeholders(data, prefix=""):
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str) and re.match(r'\$\{[A-Z_]+\}', v):
                        ref_vars.add(v)
                    elif isinstance(v, (dict, list)):
                        extract_placeholders(v, f"{prefix}{k}.")
            elif isinstance(data, list):
                for item in data:
                    extract_placeholders(item, prefix)

        extract_placeholders(ref_content)

        # 检查目标文件中的占位符
        issues = []
        for target_file_pattern in target_files:
            target_file = base / target_file_pattern
            if not target_file.exists():
                continue

            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取占位符
            target_vars = set(re.findall(r'\$\{[A-Z_]+\}', content))

            # 检查是否有未定义的占位符
            undefined = target_vars - ref_vars
            if undefined:
                issues.append(f"{target_file_pattern}: 使用了未定义的占位符: {', '.join(undefined)}")

        if issues:
            return {
                "status": "warning",  # 占位符不一致是 warning
                "detail": f"占位符一致性问题: {len(issues)} 个",
                "suggestions": issues,
            }

    except Exception as e:
        return {
            "status": "warning",
            "detail": f"占位符一致性检查失败: {str(e)}",
        }

    return {
        "status": "pass",
        "detail": "占位符使用一致",
    }


# 支持旧接口
def check(params: Dict[str, Any], artifacts: Dict[str, str], base_dir: str = ".") -> Dict[str, Any]:
    """检查函数（向后兼容）"""
    return verify(params, artifacts, base_dir)


if __name__ == "__main__":
    # 测试模式
    import json

    test_params = {
        "check_type": "file_exists",
        "required_files": [
            "devops/phase2/docker-compose.yml",
            "devops/phase2/deploy/deploy-dev-test.sh",
        ],
    }

    result = verify(test_params, {}, ".")

    print(json.dumps(result, indent=2, ensure_ascii=False))
