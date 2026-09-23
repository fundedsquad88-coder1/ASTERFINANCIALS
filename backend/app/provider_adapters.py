"""Provider adapter selection for funding rails.

Production custody is opt-in. The repository ships only a deterministic dry-run
withdrawal provider; live signing/broadcasting must be supplied by a separately
configured provider and is never enabled by accident.
"""
import os

from app.withdrawal_engine import DryRunWithdrawalProvider, WithdrawalProvider


class ProviderConfigurationError(RuntimeError):
    """Raised when a live provider is requested but not configured safely."""


class LiveWithdrawalProviderUnavailable:
    """Explicit fail-closed placeholder for a future custody integration."""

    def submit(self, withdrawal):
        raise ProviderConfigurationError(
            "Live withdrawal provider is not configured; refusing to broadcast funds"
        )


def withdrawal_provider() -> tuple[WithdrawalProvider, str]:
    mode = os.getenv("ASTER_WITHDRAWAL_PROVIDER", "dry-run").strip().lower()
    if mode in {"", "dry-run", "sandbox"}:
        return DryRunWithdrawalProvider(), "dry-run"
    if mode == "live":
        # No private key, signer, RPC wallet, or broadcast implementation lives
        # in this repository. A live adapter must be supplied separately.
        return LiveWithdrawalProviderUnavailable(), "live-unavailable"
    raise ProviderConfigurationError(
        f"Unsupported ASTER_WITHDRAWAL_PROVIDER mode: {mode}"
    )
