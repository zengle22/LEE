"""
PM Agent Security Module

Implements security measures including:
- Input sanitization and prompt injection detection
- Input/output content validation
- Rate limiting for LLM calls
- Audit logging
"""

import re
import logging
import time
import hashlib
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

from .models import Intent, ConversationContext
from .exceptions import SecurityError

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Security configuration"""
    # Prompt injection detection
    max_input_length: int = 5000
    blocked_keywords: Set[str] = field(default_factory=set)
    suspicious_patterns: List[str] = field(default_factory=list)

    # Rate limiting
    rate_limit_window: int = 60  # seconds
    rate_limit_max_requests: int = 100

    # Content validation
    max_output_length: int = 10000
    blocked_output_keywords: Set[str] = field(default_factory=set)

    # Audit logging
    enable_audit_log: bool = True
    audit_log_path: Optional[str] = None


class PromptInjectionDetector:
    """
    Detects and prevents prompt injection attacks

    Identifies:
    1. Direct instruction overrides ("ignore previous instructions")
    2. System prompt extraction ("tell me your system prompt")
    3. Delimiter injection ("```", "---")
    4. Role confusion ("you are now a different assistant")
    """

    # Suspicious patterns for prompt injection
    INJECTION_PATTERNS = [
        r'ignore\s+(all\s+)?(previous|above|the)',
        r'disregard\s+(all\s+)?(previous|above|the)',
        r'forget\s+(everything|all\s+instructions)',
        r'new\s+(instructions|role|persona)',
        r'act\s+as\s+(if\s+)?you\s+are',
        r'pretend\s+(to\s+be|you\s+are)',
        r'system\s*:\s*(prompt|instruction|message)',
        r'print\s+(your\s+)?(system\s+)?prompt',
        r'output\s+(your\s+)?(system\s+)?prompt',
        r'reveal\s+(your\s+)?(system\s+)?prompt',
        r'tell\s+me\s+(about\s+)?your\s+instructions',
        r'show\s+(me\s+)?your\s+(system\s+)?prompt',
        r'what\s+(are\s+)?your\s+instructions',
        r'how\s+(are\s+)?you\s+programmed',
        r'what\s+(are\s+)?your\s+(system\s+)?(prompt|instructions)',
        r'```',  # Code block delimiter
        r'---',  # YAML delimiter
        r'\|\|\|',  # Common delimiter
    ]

    # Blocked keywords
    BLOCKED_KEYWORDS = {
        'password', 'api_key', 'secret', 'token', 'credential',
        'private_key', 'access_key', 'auth_token',
    }

    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize prompt injection detector

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()

        # Compile regex patterns for performance
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.INJECTION_PATTERNS
        ]

        # Add custom suspicious patterns from config
        if self.config.suspicious_patterns:
            for pattern in self.config.suspicious_patterns:
                self._compiled_patterns.append(
                    re.compile(pattern, re.IGNORECASE)
                )

        # Combine blocked keywords
        self._blocked_keywords = self.BLOCKED_KEYWORDS.copy()
        self._blocked_keywords.update(self.config.blocked_keywords)

    def sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input

        Args:
            user_input: Raw user input

        Returns:
            Sanitized input

        Raises:
            SecurityError: If input is blocked
        """
        # Check length
        if len(user_input) > self.config.max_input_length:
            raise SecurityError(
                f"Input exceeds maximum length of {self.config.max_input_length}",
                security_issue="input_too_long"
            )

        # Check for prompt injection patterns
        for pattern in self._compiled_patterns:
            if pattern.search(user_input):
                logger.warning(f"Potential prompt injection detected: {pattern.pattern}")
                raise SecurityError(
                    "Input contains suspicious patterns that may indicate prompt injection",
                    security_issue="prompt_injection"
                )

        # Check for blocked keywords
        input_lower = user_input.lower()
        for keyword in self._blocked_keywords:
            if keyword in input_lower:
                logger.warning(f"Blocked keyword detected: {keyword}")
                raise SecurityError(
                    f"Input contains blocked keyword: {keyword}",
                    security_issue="blocked_keyword"
                )

        return user_input

    def validate_output(self, output: str, user_input: str) -> bool:
        """
        Validate LLM output for potential leaks

        Args:
            output: LLM output
            user_input: Original user input (for context)

        Returns:
            True if output is safe

        Raises:
            SecurityError: If output is suspicious
        """
        # Check for system prompt leakage
        leakage_indicators = [
            'system:',
            'system prompt:',
            'instructions:',
            'as an ai',
            'as a language model',
        ]

        output_lower = output.lower()
        for indicator in leakage_indicators:
            if indicator in output_lower and indicator not in user_input.lower():
                logger.warning(f"Potential system prompt leakage detected: {indicator}")
                raise SecurityError(
                    "Output may contain system prompt information",
                    security_issue="prompt_leakage"
                )

        # Check for blocked output keywords
        for keyword in self.config.blocked_output_keywords:
            if keyword in output_lower:
                logger.warning(f"Blocked output keyword detected: {keyword}")
                raise SecurityError(
                    f"Output contains blocked keyword: {keyword}",
                    security_issue="blocked_output"
                )

        # Check length
        if len(output) > self.config.max_output_length:
            logger.warning(f"Output exceeds maximum length: {len(output)}")
            raise SecurityError(
                f"Output exceeds maximum length of {self.config.max_output_length}",
                security_issue="output_too_long"
            )

        return True


class RateLimiter:
    """
    Rate limiter for LLM API calls

    Implements sliding window rate limiting to prevent abuse
    and control API costs.
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize rate limiter

        Args:
            config: Security configuration with rate limit settings
        """
        self.config = config or SecurityConfig()

        # Request tracking: {session_id: deque of timestamps}
        self._requests: Dict[str, deque] = defaultdict(deque)

        # Cleanup timestamp
        self._last_cleanup = time.time()

    def check_rate_limit(self, session_id: str) -> bool:
        """
        Check if request is within rate limit

        Args:
            session_id: Session or user identifier

        Returns:
            True if within rate limit

        Raises:
            SecurityError: If rate limit exceeded
        """
        now = time.time()
        window_start = now - self.config.rate_limit_window

        # Periodic cleanup of old entries
        if now - self._last_cleanup > 300:  # Every 5 minutes
            self._cleanup_old_entries(window_start)
            self._last_cleanup = now

        # Get request queue for session
        requests = self._requests[session_id]

        # Remove old requests outside the window
        while requests and requests[0] < window_start:
            requests.popleft()

        # Check if within limit
        if len(requests) >= self.config.rate_limit_max_requests:
            logger.warning(f"Rate limit exceeded for session: {session_id}")
            raise SecurityError(
                f"Rate limit exceeded: max {self.config.rate_limit_max_requests} "
                f"requests per {self.config.rate_limit_window} seconds",
                security_issue="rate_limit_exceeded"
            )

        # Record this request
        requests.append(now)
        return True

    def _cleanup_old_entries(self, window_start: float):
        """Clean up old request entries across all sessions"""
        for session_id, requests in list(self._requests.items()):
            while requests and requests[0] < window_start:
                requests.popleft()

            # Remove empty queues
            if not requests:
                del self._requests[session_id]

    def get_request_count(self, session_id: str, window: Optional[int] = None) -> int:
        """
        Get request count for a session

        Args:
            session_id: Session identifier
            window: Time window in seconds (default: from config)

        Returns:
            Number of requests in the window
        """
        window = window or self.config.rate_limit_window
        now = time.time()
        window_start = now - window

        requests = self._requests.get(session_id, deque())

        return sum(1 for ts in requests if ts >= window_start)


class AuditLogger:
    """
    Audit logger for security-relevant events

    Logs all security decisions and potential threats for
    compliance and forensics.
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize audit logger

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()
        self._enabled = self.config.enable_audit_log

    def log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        session_id: Optional[str] = None
    ):
        """
        Log a security event

        Args:
            event_type: Type of security event
            details: Event details
            session_id: Optional session identifier
        """
        if not self._enabled:
            return

        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'session_id': session_id,
            'details': details,
        }

        # Log to file if configured
        if self.config.audit_log_path:
            try:
                import json
                with open(self.config.audit_log_path, 'a') as f:
                    f.write(json.dumps(event) + '\n')
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

        # Also log to standard logger
        logger.info(f"Audit: {event_type} - {details}")

    def log_prompt_injection_blocked(self, user_input: str, session_id: Optional[str] = None):
        """Log blocked prompt injection attempt"""
        # Create hash of input (don't log potentially malicious input directly)
        input_hash = hashlib.sha256(user_input.encode()).hexdigest()[:16]

        self.log_security_event(
            'prompt_injection_blocked',
            {
                'input_hash': input_hash,
                'input_length': len(user_input),
            },
            session_id
        )

    def log_rate_limit_exceeded(self, session_id: str):
        """Log rate limit exceeded"""
        self.log_security_event(
            'rate_limit_exceeded',
            {
                'session_id': session_id,
            },
            session_id
        )

    def log_permission_denied(
        self,
        intent_type: str,
        reason: str,
        session_id: Optional[str] = None
    ):
        """Log permission denial"""
        self.log_security_event(
            'permission_denied',
            {
                'intent_type': intent_type,
                'reason': reason,
            },
            session_id
        )


class SecurityManager:
    """
    Centralized security manager

    Combines all security components into a single interface
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize security manager

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()

        self.injection_detector = PromptInjectionDetector(config)
        self.rate_limiter = RateLimiter(config)
        self.audit_logger = AuditLogger(config)

    def sanitize_and_validate_input(
        self,
        user_input: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Sanitize and validate user input

        Args:
            user_input: Raw user input
            session_id: Optional session ID

        Returns:
            Sanitized input

        Raises:
            SecurityError: If input fails validation
        """
        # Check rate limit first
        if session_id:
            self.rate_limiter.check_rate_limit(session_id)

        # Sanitize input
        sanitized = self.injection_detector.sanitize_input(user_input)

        return sanitized

    def validate_output(
        self,
        output: str,
        user_input: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Validate LLM output

        Args:
            output: LLM output
            user_input: Original user input
            session_id: Optional session ID

        Returns:
            True if output is valid

        Raises:
            SecurityError: If output fails validation
        """
        return self.injection_detector.validate_output(output, user_input)

    def log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        session_id: Optional[str] = None
    ):
        """Log a security event"""
        self.audit_logger.log_security_event(event_type, details, session_id)

    def get_metrics(self) -> Dict[str, Any]:
        """Get security metrics"""
        return {
            "injection_detector": {
                "patterns_loaded": len(self.injection_detector._compiled_patterns),
                "blocked_keywords": len(self.injection_detector._blocked_keywords),
            },
            "rate_limiter": {
                "active_sessions": len(self.rate_limiter._requests),
            },
        }
