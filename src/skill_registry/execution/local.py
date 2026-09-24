from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from time import monotonic
from typing import Sequence

from .base import ExecutionResult, SkillExecutionError


def _output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class LocalExecutionProvider:
    """Execute skill resources in a child process on the registry host."""

    def __init__(self, python_executable: str | None = None) -> None:
        self._python_executable = python_executable or sys.executable

    @property
    def name(self) -> str:
        return "local"

    def execute(
        self,
        resource_path: Path,
        arguments: Sequence[str] = (),
        timeout: float | None = None,
    ) -> ExecutionResult:
        try:
            path = resource_path.resolve(strict=True)
        except OSError as error:
            raise SkillExecutionError(
                f"Executable resource cannot be resolved: {resource_path}"
            ) from error
        if not path.is_file():
            raise SkillExecutionError(f"Executable resource is not a file: {path}")
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be greater than 0")
        if isinstance(arguments, (str, bytes)) or any(
            not isinstance(argument, str) for argument in arguments
        ):
            raise ValueError("arguments must be a sequence of strings")

        command = self._command(path, arguments)
        started_at = monotonic()
        try:
            import os

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            completed = subprocess.run(
                command,
                cwd=path.parent,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            return ExecutionResult(
                provider=self.name,
                exit_code=None,
                stdout=_output_text(error.stdout),
                stderr=_output_text(error.stderr),
                timed_out=True,
                duration_ms=self._elapsed_ms(started_at),
            )
        except OSError as error:
            raise SkillExecutionError(
                f"Failed to start executable resource {path.name}: {error}"
            ) from error

        return ExecutionResult(
            provider=self.name,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timed_out=False,
            duration_ms=self._elapsed_ms(started_at),
        )

    def _command(self, path: Path, arguments: Sequence[str]) -> list[str]:
        if path.suffix.lower() == ".py":
            return [self._python_executable, str(path), *arguments]
        return [str(path), *arguments]

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, round((monotonic() - started_at) * 1000))
