from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


class SkillExecutionError(RuntimeError):
    """Raised when an execution provider cannot start a skill resource."""


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Structured result returned by every execution provider."""

    provider: str
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int

    @property
    def success(self) -> bool:
        return not self.timed_out and self.exit_code == 0


class SkillExecutionProvider(Protocol):
    """Backend contract used by the registry to execute a skill resource."""

    @property
    def name(self) -> str:
        ...

    def execute(
        self,
        resource_path: Path,
        arguments: Sequence[str] = (),
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Execute one already-resolved resource path."""
        ...
