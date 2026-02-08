"""Verifier base classes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from abc import ABC, abstractmethod


class VerifyStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class VerifyResult:
    status: VerifyStatus
    verifier_id: str
    message: str
    details: Optional[Dict] = None


class BaseVerifier(ABC):
    @property
    @abstractmethod
    def verifier_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, context: Dict) -> VerifyResult:
        raise NotImplementedError
