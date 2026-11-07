"""Auto-Invest execution provider boundary.

Execution is intentionally fail-closed. A production strategy adapter must be
provided separately; this repository does not contain trading keys, exchange
credentials, or market-order broadcasting.
"""
from dataclasses import dataclass
from typing import Protocol

from app.main import AutoInvest


@dataclass(frozen=True)
class ExecutionResult:
    autoinvest_id: int
    provider_reference: str


class AutoInvestExecutionProvider(Protocol):
    def execute(self, position: AutoInvest) -> ExecutionResult:
        """Execute or reconcile one strategy position externally."""


class FailClosedExecutionProvider:
    def execute(self, position: AutoInvest) -> ExecutionResult:
        raise RuntimeError("Auto-Invest execution provider is not configured")


def execution_provider() -> tuple[AutoInvestExecutionProvider, str]:
    import os

    mode = os.getenv("ASTER_AUTOINVEST_EXECUTION_PROVIDER", "disabled").strip().lower()
    if mode in {"", "disabled", "fail-closed"}:
        return FailClosedExecutionProvider(), "disabled"
    raise RuntimeError(
        f"Unsupported ASTER_AUTOINVEST_EXECUTION_PROVIDER mode: {mode}"
    )
