"""BuildResult — structured return type for every geometry operation.

Every kernel function returns a BuildResult. The AI gets structured feedback
with diagnostics and hints, not raw exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BuildResult:
    """Result of a geometry operation."""

    shape: Any | None
    valid: bool
    volume: float | None = None
    diagnostics: dict = field(default_factory=dict)
    code_violations: list[dict] = field(default_factory=list)
    affected_rooms: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if shape exists and geometry is valid."""
        return self.shape is not None and self.valid

    @property
    def has_errors(self) -> bool:
        """True if any code violation has severity 'error'."""
        return any(v.get("severity") == "error" for v in self.code_violations)

    @classmethod
    def fail(cls, reason: str, hint: str | None = None) -> BuildResult:
        """Create a failure result with diagnostics."""
        diag: dict = {"reason": reason}
        if hint is not None:
            diag["hint"] = hint
        return cls(shape=None, valid=False, diagnostics=diag)
