"""Execution provider abstractions for skill resources."""

from .base import ExecutionResult, SkillExecutionError, SkillExecutionProvider
from .local import LocalExecutionProvider

__all__ = [
    "ExecutionResult",
    "LocalExecutionProvider",
    "SkillExecutionError",
    "SkillExecutionProvider",
]
