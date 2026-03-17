#!/usr/bin/env python3
"""
Fitness Rule Schema 验证工具
支持 YAML/JSON 双格式，输出结构化错误信息

Usage:
    python validate_fitness_rule.py <file1> [file2 ...] [--schema <schema_path>] [--output text|json]
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
from jsonschema import Draft202012Validator, ValidationError

try:
    from ruamel.yaml import YAML
    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False
    import yaml


class StructuredError:
    """结构化错误输出"""
    def __init__(self, message: str, path: str, line: Optional[int] = None,
                 schema_path: Optional[str] = None):
        self.message = message
        self.path = path  # JSONPath 风格字段路径
        self.line = line  # YAML 行号
        self.schema_path = schema_path  # Schema 验证路径

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "message": self.message,
            "path": self.path,
        }
        if self.line is not None:
            result["line"] = self.line
        if self.schema_path:
            result["schema_path"] = self.schema_path
        return result


class FitnessRuleValidator:
    """Fitness Rule 验证器"""

    def __init__(self, schema_path: Path):
        self.schema = self._load_schema(schema_path)
        self.validator = Draft202012Validator(self.schema)
        self.yaml_parser = None
        if HAS_RUAMEL:
            self.yaml_parser = YAML()
            self.yaml_parser.preserve_quotes = True

    def _load_schema(self, path: Path) -> Dict[str, Any]:
        """加载 JSON Schema 文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def validate_file(self, file_path: Path) -> List[StructuredError]:
        """验证单个文件"""
        errors = []

        # 1. 加载文件（自动检测格式）
        data = self._load_file(file_path)
        if data is None:
            errors.append(StructuredError(
                message="无法解析文件：请检查 YAML/JSON 格式是否正确",
                path="$",
                line=1
            ))
            return errors

        # 2. Schema 验证
        for error in self.validator.iter_errors(data):
            structured = self._convert_error(error, file_path)
            errors.append(structured)

        # 3. 额外验证：pass_criteria 条件分支（备份方案）
        extra_errors = self._validate_pass_criteria(data)
        errors.extend(extra_errors)

        return errors

    def _load_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """加载 YAML/JSON 文件"""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 自动检测格式
        if path.suffix.lower() in ['.yaml', '.yml']:
            return self._load_yaml(content)
        elif path.suffix.lower() == '.json':
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        else:
            # 尝试 YAML 优先
            try:
                return self._load_yaml(content)
            except:
                try:
                    return json.loads(content)
                except:
                    return None

    def _load_yaml(self, content: str) -> Optional[Dict[str, Any]]:
        """加载 YAML 内容"""
        if HAS_RUAMEL:
            return self.yaml_parser.load(content)
        else:
            return yaml.safe_load(content)

    def _convert_error(self, error: ValidationError, file_path: Path) -> StructuredError:
        """将 jsonschema 错误转换为结构化错误"""
        # 构建 JSONPath 风格路径
        path = "$" + "".join(
            f".{p}" if isinstance(p, str) else f"[{p}]"
            for p in error.absolute_path
        )

        # 尝试获取行号
        line = self._get_line_number(error.absolute_path, file_path)

        # 构建 schema 路径
        schema_path = "->".join(str(p) for p in error.schema_path)

        return StructuredError(
            message=error.message,
            path=path,
            line=line,
            schema_path=schema_path
        )

    def _get_line_number(self, absolute_path, file_path: Path) -> Optional[int]:
        """尝试获取 YAML 行号"""
        if not HAS_RUAMEL:
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            yaml_obj = self.yaml_parser.load(content)

            # ruamel.yaml 0.17+ API
            if hasattr(yaml_obj, 'ca') and hasattr(yaml_obj.ca, 'items'):
                # 尝试通过路径导航获取行号
                current = yaml_obj
                for p in absolute_path:
                    if isinstance(p, int) and isinstance(current, list):
                        if p < len(current):
                            current = current[p]
                        else:
                            return None
                    elif isinstance(p, str) and isinstance(current, dict):
                        if p in current:
                            current = current[p]
                        else:
                            return None

                # 获取注释信息中的行号
                if hasattr(current, 'lc') and hasattr(current.lc, 'line'):
                    return current.lc.line + 1  # 行号从 1 开始
        except Exception:
            pass

        return None

    def _validate_pass_criteria(self, data: Dict[str, Any]) -> List[StructuredError]:
        """
        手动验证 pass_criteria 条件分支（备份方案）
        用于处理 jsonschema 条件验证可能的兼容性问题
        """
        errors = []
        pass_criteria = data.get("pass_criteria", {})
        kind = pass_criteria.get("kind")

        if not kind:
            return errors

        path_base = "$.pass_criteria"

        if kind == "exit_code" and "exit_code" not in pass_criteria:
            errors.append(StructuredError(
                message="当 kind 为 'exit_code' 时，必须指定 'exit_code' 字段",
                path=f"{path_base}",
                schema_path="pass_criteria/if-then[exit_code]"
            ))
        elif kind == "regex_match" and "pattern" not in pass_criteria:
            errors.append(StructuredError(
                message="当 kind 为 'regex_match' 时，必须指定 'pattern' 字段",
                path=f"{path_base}",
                schema_path="pass_criteria/if-then[regex_match]"
            ))
        elif kind == "json_path" and "json_path" not in pass_criteria:
            errors.append(StructuredError(
                message="当 kind 为 'json_path' 时，必须指定 'json_path' 字段",
                path=f"{path_base}",
                schema_path="pass_criteria/if-then[json_path]"
            ))
        elif kind == "json_path" and "expected_value" not in pass_criteria:
            errors.append(StructuredError(
                message="当 kind 为 'json_path' 时，必须指定 'expected_value' 字段",
                path=f"{path_base}",
                schema_path="pass_criteria/if-then[json_path]"
            ))
        elif kind == "file_exists" and "file_path" not in pass_criteria:
            errors.append(StructuredError(
                message="当 kind 为 'file_exists' 时，必须指定 'file_path' 字段",
                path=f"{path_base}",
                schema_path="pass_criteria/if-then[file_exists]"
            ))

        return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate fitness rule files against schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python validate_fitness_rule.py rule.yaml
    python validate_fitness_rule.py rule.yaml rule.json --output json
    python validate_fitness_rule.py rule.yaml --schema ./schema.json
        """
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="fitness rule files to validate (YAML or JSON)"
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).parent / "fitness_rule.schema.json",
        help="Path to JSON schema file (default: same directory as script)"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # 检查 schema 文件是否存在
    if not args.schema.exists():
        print(f"Error: Schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(2)

    validator = FitnessRuleValidator(args.schema)
    all_passed = True
    results = []

    for file_path in args.files:
        if not file_path.exists():
            results.append({
                "file": str(file_path),
                "valid": False,
                "errors": [{
                    "message": "文件不存在",
                    "path": "$",
                    "line": 1
                }]
            })
            all_passed = False
            continue

        errors = validator.validate_file(file_path)

        if errors:
            all_passed = False
            results.append({
                "file": str(file_path),
                "valid": False,
                "errors": [e.to_dict() for e in errors]
            })
        else:
            results.append({
                "file": str(file_path),
                "valid": True,
                "errors": []
            })

    # 输出结果
    if args.output == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            if result["valid"]:
                print(f"✓ {result['file']}: PASS")
            else:
                print(f"✗ {result['file']}: FAIL")
                for err in result["errors"]:
                    line_info = f":{err['line']}" if err.get('line') else ""
                    print(f"  {err['path']}{line_info}: {err['message']}")
                    if args.verbose and err.get('schema_path'):
                        print(f"    Schema path: {err['schema_path']}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
