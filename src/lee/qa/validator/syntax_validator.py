"""
QA Module - Syntax Validator (Layer 2)

Validates Python syntax and basic semantics using AST.
Layer 2 of the validation pyramid.
"""

import ast
import sys
from typing import List, Set, Dict, Any

from lee.qa.validator.result import ValidationResult


class SyntaxValidator:
    """
    Syntax validator (Layer 2).

    Uses Python AST to validate syntax and perform basic semantic checks.
    """

    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        """
        Validate Python syntax and semantics.

        Args:
            code: Generated Python code

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult()

        try:
            # 1. Parse AST
            tree = ast.parse(code)

        except SyntaxError as e:
            result.add_error(
                "syntax_error",
                f"行 {e.lineno}: {e.msg}",
                line_number=e.lineno
            )
            return result

        # 2. Semantic checks
        checker = SemanticChecker()
        try:
            checker.visit(tree)
        except Exception as e:
            result.add_error("semantic_error", str(e))

        # 3. Add checker findings
        for error in checker.errors:
            result.add_error("semantic", error["message"], line_number=error.get("line"))

        # 4. Add warnings
        for warning in checker.warnings:
            result.add_warning(warning["category"], warning["message"],
                            line_number=warning.get("line"))

        return result


class SemanticChecker(ast.NodeVisitor):
    """AST visitor for semantic checks"""

    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.imports: Set[str] = set()
        self.test_functions: List[Dict] = []

    def visit_Import(self, node: ast.Import):
        """Track imports"""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports"""
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check test functions"""
        if node.name.startswith("test_"):
            self.test_functions.append({
                "name": node.name,
                "line": node.lineno,
                "args": [arg.arg for arg in node.args.args],
            })

            # Check for page parameter
            arg_names = [arg.arg for arg in node.args.args]
            if "page" not in arg_names:
                self.errors.append({
                    "category": "missing_page_param",
                    "message": f"测试函数 '{node.name}' 缺少 'page' 参数",
                    "line": node.lineno,
                })

            # Check for docstring
            docstring = ast.get_docstring(node)
            if not docstring:
                self.warnings.append({
                    "category": "missing_docstring",
                    "message": f"测试函数 '{node.name}' 缺少 docstring",
                    "line": node.lineno,
                })

            # Check function body has statements
            if len(node.body) == 0 or (
                len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
            ):
                self.errors.append({
                    "category": "empty_function",
                    "message": f"测试函数 '{node.name}' 是空的",
                    "line": node.lineno,
                })

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Check async function definitions"""
        # Same checks as regular functions
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Track class definitions"""
        # Warn against classes in test files (usually unnecessary)
        if node.name.startswith("Test"):
            self.warnings.append({
                "category": "test_class",
                "message": f"测试类 '{node.name}' 可能是不必要的，推荐使用函数式测试",
                "line": node.lineno,
            })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Check function calls for common issues"""
        # Check for hardcoded waits
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "wait_for_timeout":
                self.warnings.append({
                    "category": "hardcoded_wait",
                    "message": "使用了 wait_for_timeout，推荐使用 wait_for_* 方法",
                    "line": node.lineno,
                })

        self.generic_visit(node)
