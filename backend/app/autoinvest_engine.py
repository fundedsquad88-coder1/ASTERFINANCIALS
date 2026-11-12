"""Fail-closed Auto-Invest execution boundary.

The API can create and release positions, but this engine never invents
performance. A live strategy provider must explicitly implement the protocol
and return a timestamped valuation before any valuation is persisted.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import AutoInvest, StrategyValuation, ValuationSource, validate_valuation


@dataclass(frozen=True)
class StrategyExecutionResult:
    autoinvest_id: int
    value: Decimal
    as_of: datetime
    source: str


class AutoInvestExecutionProvider(Protocol):
    def value(self, position: AutoInvest) -> StrategyExecutionResult:
        """Return an independently produced, timestamped strategy valuation."""


class FailClosedAutoInvestProvider:
    def value(self, position: AutoInvest) -> StrategyExecutionResult:
        raise RuntimeError("Auto-Invest execution provider is not configured")


def sync_active_valuations(
    dbs: Session,
    provider: AutoInvestExecutionProvider | None = None,
    *,
    limit: int = 100,
) -> list[dict[str, object]]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    provider = provider or FailClosedAutoInvestProvider()
    positions = dbs.scalars(
        select(AutoInvest)
        .where(AutoInvest.status == "active")
        .order_by(AutoInvest.id.asc())
        .limit(limit)
    ).all()

    results: list[dict[str, object]] = []
    for position in positions:
        result = provider.value(position)
        validate_valuation(result.value, result.as_of)
        dbs.add(
            StrategyValuation(
                autoinvest_id=position.id,
                value=result.value,
                source=result.source,
                as_of=result.as_of,
            )
        )
        results.append(
            {
                "autoinvest_id": position.id,
                "value": str(result.value),
                "as_of": result.as_of.isoformat(),
                "source": result.source,
            }
        )
    dbs.commit()
    return results


def provider_status(dbs: Session) -> list[dict[str, object]]:
    rows = dbs.scalars(select(ValuationSource).order_by(ValuationSource.strategy.asc())).all()
    return [
        {
            "strategy": row.strategy,
            "provider": row.provider,
            "enabled": row.enabled,
            "last_sync_at": row.last_sync_at,
            "last_error": row.last_error,
        }
        for row in rows
    ]


def sync_status(dbs: Session, *, limit: int = 100) -> dict[str, object]:
    """Run one fail-closed valuation cycle and expose an operational summary."""
    try:
        items = sync_active_valuations(dbs, limit=limit)
        return {"ok": True, "status": "synced", "count": len(items), "items": items}
    except RuntimeError as exc:
        dbs.rollback()
        return {"ok": False, "status": "provider_unavailable", "count": 0, "items": [], "error": str(exc)}
    except ValueError:
        dbs.rollback()
        raise
