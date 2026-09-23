"""Sandbox-first withdrawal execution engine.

This module owns the state transition from an internal pending withdrawal to a
provider submission. It deliberately contains no private-key handling and the
default provider is a dry-run adapter. A real broadcaster must implement the
same protocol and be explicitly enabled outside the repository.
"""
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.funding import WithdrawalRequest
from app.main import AuditEvent, LedgerEntry, Wallet, post_double_entry


@dataclass(frozen=True)
class BroadcastResult:
    provider_reference: str
    tx_hash: str | None = None


class WithdrawalProvider(Protocol):
    def submit(self, withdrawal: WithdrawalRequest) -> BroadcastResult:
        """Submit a withdrawal to an external custody/provider rail."""


class DryRunWithdrawalProvider:
    """Deterministic provider for CI/staging; never signs or broadcasts funds."""

    def submit(self, withdrawal: WithdrawalRequest) -> BroadcastResult:
        return BroadcastResult(
            provider_reference=withdrawal.provider_reference or f"AST-WD-{withdrawal.id}",
            tx_hash=f"DRYRUN-{withdrawal.id}",
        )


def _audit(dbs: Session, row: WithdrawalRequest, event_type: str, **metadata: object) -> None:
    import json
    dbs.add(
        AuditEvent(
            user_id=row.user_id,
            event_type=event_type,
            metadata_json=json.dumps(metadata, default=str),
        )
    )


def process_pending_withdrawals(
    dbs: Session,
    provider: WithdrawalProvider | None = None,
    *,
    limit: int = 25,
) -> list[dict[str, object]]:
    """Submit pending withdrawals idempotently.

    Only pending requests are claimed. A provider exception rolls the
    transaction back and leaves the request pending for a later retry.
    """
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    provider = provider or DryRunWithdrawalProvider()
    rows = dbs.scalars(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.status == "pending")
        .order_by(WithdrawalRequest.id.asc())
        .limit(limit)
        .with_for_update()
    ).all()

    results: list[dict[str, object]] = []
    for row in rows:
        try:
            result = provider.submit(row)
            row.provider_reference = result.provider_reference
            row.status = "submitted"
            _audit(
                dbs,
                row,
                "withdrawal_submitted",
                withdrawal_id=row.id,
                provider_reference=result.provider_reference,
                tx_hash=result.tx_hash,
                dry_run=isinstance(provider, DryRunWithdrawalProvider),
            )
            results.append(
                {
                    "id": row.id,
                    "status": row.status,
                    "provider_reference": result.provider_reference,
                    "tx_hash": result.tx_hash,
                }
            )
        except Exception as exc:
            dbs.rollback()
            raise RuntimeError(f"Withdrawal {row.id} submission failed") from exc

    dbs.commit()
    return results


def reconcile_withdrawal_confirmation(
    dbs: Session,
    *,
    provider_reference: str,
    tx_hash: str | None = None,
) -> dict[str, object]:
    """Finalize a provider-confirmed withdrawal exactly once.

    The user.pending balance is released only after the provider confirms the
    transaction. Duplicate confirmations are safe.
    """
    row = dbs.scalar(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.provider_reference == provider_reference)
        .with_for_update()
    )
    if not row:
        raise ValueError("Withdrawal not found")
    if row.status == "confirmed":
        return {"id": row.id, "status": "confirmed", "duplicate": True}
    if row.status not in {"submitted", "pending"}:
        raise ValueError(f"Withdrawal is not confirmable from {row.status}")

    wallet = dbs.scalar(
        select(Wallet).where(Wallet.user_id == row.user_id).with_for_update()
    )
    if not wallet:
        raise ValueError("Wallet not found")
    if wallet.pending < row.amount:
        raise ValueError("Pending wallet balance is below withdrawal amount")

    settlement_ref = f"WD-{provider_reference}-SETTLED"
    post_double_entry(
        dbs,
        user_id=row.user_id,
        reference=settlement_ref,
        amount=row.amount,
        debit_account="platform.withdrawals",
        credit_account="user.pending",
    )
    wallet.pending -= row.amount
    row.status = "confirmed"

    original_ref = f"WD-{provider_reference}"
    entry = dbs.scalar(select(LedgerEntry).where(LedgerEntry.reference == original_ref))
    if entry:
        entry.status = "posted"
    _audit(
        dbs,
        row,
        "withdrawal_confirmed",
        withdrawal_id=row.id,
        tx_hash=tx_hash,
    )
    dbs.commit()
    return {"id": row.id, "status": row.status, "tx_hash": tx_hash, "duplicate": False}


def reconcile_withdrawal_failure(
    dbs: Session,
    *,
    provider_reference: str,
    reason: str = "provider_failed",
) -> dict[str, object]:
    """Return reserved funds to available balance after provider failure."""
    row = dbs.scalar(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.provider_reference == provider_reference)
        .with_for_update()
    )
    if not row:
        raise ValueError("Withdrawal not found")
    if row.status in {"failed", "reversed"}:
        return {"id": row.id, "status": row.status, "duplicate": True}
    if row.status not in {"submitted", "pending"}:
        raise ValueError(f"Withdrawal is not releasable from {row.status}")

    wallet = dbs.scalar(
        select(Wallet).where(Wallet.user_id == row.user_id).with_for_update()
    )
    if not wallet:
        raise ValueError("Wallet not found")
    if wallet.pending < row.amount:
        raise ValueError("Pending wallet balance is below withdrawal amount")

    release_ref = f"WD-{provider_reference}-RELEASE"
    post_double_entry(
        dbs,
        user_id=row.user_id,
        reference=release_ref,
        amount=row.amount,
        debit_account="user.available",
        credit_account="user.pending",
    )
    wallet.pending -= row.amount
    wallet.available += row.amount
    row.status = "failed"

    original_ref = f"WD-{provider_reference}"
    entry = dbs.scalar(select(LedgerEntry).where(LedgerEntry.reference == original_ref))
    if entry:
        entry.status = "reversed"
    dbs.add(
        LedgerEntry(
            user_id=row.user_id,
            kind="withdrawal_reversal",
            amount=row.amount,
            reference=release_ref,
            currency=row.currency,
            status="posted",
        )
    )
    _audit(
        dbs,
        row,
        "withdrawal_released",
        withdrawal_id=row.id,
        reason=reason,
    )
    dbs.commit()
    return {"id": row.id, "status": row.status, "duplicate": False}
