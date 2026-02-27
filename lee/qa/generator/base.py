"""
QA Module - Generator Base

Base class for code generators.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from lee.qa.validator.result import ValidationResult, CodeGenerationError


@dataclass
class GenerationRequest:
    """Code generation request"""
    test_cases: List[Dict]
    base_url: str
    framework: str = "playwright"
    options: Dict[str, Any] = None

    def __post_init__(self):
        if self.options is None:
            self.options = {}


@dataclass
class GenerationResult:
    """Code generation result"""
    code: str
    files: Dict[str, str]  # filename -> content
    validation: ValidationResult
    retries: int = 0


class BaseGenerator(ABC):
    """
    Base class for code generators.

    Generators are responsible for converting test cases into executable code.
    They use LLM for code generation and include multi-layer validation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Generator name"""
        pass

    @property
    @abstractmethod
    def framework(self) -> str:
        """Supported framework"""
        pass

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate code with validation and retry.

        Args:
            request: Generation request with test cases and configuration

        Returns:
            GenerationResult with code and validation results
        """
        pass

    @abstractmethod
    def _llm_generate(self, request: GenerationRequest) -> str:
        """
        Call LLM to generate code.

        Args:
            request: Generation request

        Returns:
            Generated code string
        """
        pass

    def _validate_and_retry(
        self,
        request: GenerationRequest,
        max_retries: int = 3
    ) -> GenerationResult:
        """
        Generate code with validation and retry on failure.

        Args:
            request: Generation request
            max_retries: Maximum number of retry attempts

        Returns:
            GenerationResult

        Raises:
            CodeGenerationError: If validation fails after all retries
        """
        from lee.qa.validator.schema_validator import SchemaValidator
        from lee.qa.validator.syntax_validator import SyntaxValidator

        for attempt in range(max_retries):
            # 1. Generate code
            code = self._llm_generate(request)

            # 2. Schema validation (Layer 1)
            schema_result = SchemaValidator.validate(code)
            if not schema_result.is_valid:
                code = self._retry_with_schema_feedback(
                    request, code, schema_result.errors
                )
                continue

            # 3. Syntax validation (Layer 2)
            syntax_result = SyntaxValidator.validate(code)
            if not syntax_result.is_valid:
                code = self._retry_with_syntax_feedback(
                    request, code, syntax_result.errors
                )
                continue

            # 4. Static analysis (Layer 3)
            static_result = self._static_analysis(code)
            if static_result.warnings:
                # Warnings don't block execution, but log them
                pass

            return GenerationResult(
                code=code,
                files=self._split_into_files(code),
                validation=ValidationResult.merge(
                    schema_result, syntax_result, static_result
                ),
                retries=attempt,
            )

        # Retries exhausted
        raise CodeGenerationError(
            f"Failed to generate valid code after {max_retries} attempts",
            last_validation=schema_result if schema_result else None,
        )

    def _retry_with_schema_feedback(
        self,
        request: GenerationRequest,
        code: str,
        errors: List[Dict]
    ) -> str:
        """Retry generation with schema validation feedback"""
        feedback_prompt = self._build_feedback_prompt(code, errors, "schema")
        return self._llm_generate_with_feedback(request, feedback_prompt)

    def _retry_with_syntax_feedback(
        self,
        request: GenerationRequest,
        code: str,
        errors: List[Dict]
    ) -> str:
        """Retry generation with syntax validation feedback"""
        feedback_prompt = self._build_feedback_prompt(code, errors, "syntax")
        return self._llm_generate_with_feedback(request, feedback_prompt)

    def _build_feedback_prompt(
        self,
        code: str,
        errors: List[Dict],
        error_type: str
    ) -> str:
        """Build feedback prompt for retry"""
        feedback = f"The generated code has {error_type} errors:\n\n"
        for error in errors:
            feedback += f"- {error['category']}: {error['message']}\n"
        feedback += f"\nPlease fix these errors and regenerate the code.\n"
        return feedback

    def _llm_generate_with_feedback(
        self,
        request: GenerationRequest,
        feedback_prompt: str
    ) -> str:
        """Generate with feedback - default implementation calls base _llm_generate"""
        # Subclasses can override for more sophisticated retry logic
        return self._llm_generate(request)

    def _static_analysis(self, code: str) -> ValidationResult:
        """Perform static analysis on generated code (Layer 3)"""
        from lee.qa.validator.selector_validator import SelectorValidator
        from lee.qa.validator.timeout_validator import TimeoutValidator

        result = ValidationResult()

        # Selector quality check
        selector_result = SelectorValidator.validate_selectors_in_code(code)
        if selector_result.get("avg_score", 1.0) < 0.7:
            result.add_warning(
                "selector_quality",
                f"Average selector stability score: {selector_result.get('avg_score', 0):.2f}"
            )

        # Timeout configuration check
        timeout_result = TimeoutValidator.validate(code)
        result.warnings.extend(timeout_result.warnings)
        result.errors.extend(timeout_result.errors)

        return result

    def _split_into_files(self, code: str) -> Dict[str, str]:
        """
        Split generated code into multiple files.

        Default implementation returns a single file.
        Subclasses can override for more sophisticated splitting.
        """
        return {
            "test_main.py": code,
        }
