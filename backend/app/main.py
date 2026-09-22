        return scan_once(dbs)
    except Exception as exc:
        dbs.rollback()
        raise HTTPException(502, f"Blockchain scan failed: {type(exc).__name__}")

@app.get("/v1/production/status")
def production_status():
    return {
        "api": "ready",
        "database": "configured" if os.getenv("DATABASE_URL") else "local-development-fallback",
        "funding_provider": bool(os.getenv("ASTER_FUNDING_PROVIDER") or os.getenv("ASTER_FUNDING_WEBHOOK_SECRET")),
        "blockchain_bep20_rpc": bool(os.getenv("ASTER_BSC_RPC_URL")),
        "blockchain_trc20_api": bool(os.getenv("ASTER_TRON_API_KEY") or os.getenv("ASTER_TRON_API_URL")),
        "email_provider": bool(os.getenv("ASTER_EMAIL_PROVIDER")),
        "auto_invest_execution_provider": bool(os.getenv("ASTER_AUTOINVEST_PROVIDER")),
        "valuation_provider": bool(os.getenv("ASTER_VALUATION_PROVIDER")),
        "push_provider": bool(os.getenv("ASTER_PUSH_PROVIDER")),
        "note": "Features without a configured provider remain fail-closed; the API never fabricates settlement or performance."
    }

@app.get("/v1/admin/treasury/summary")
def admin_treasury_summary(x_aster_admin_key: Optional[str] = Header(default=None, alias="X-Aster-Admin-Key"), dbs: Session = Depends(db)):
    expected = os.getenv("ASTER_ADMIN_API_KEY", "")
    if len(expected) < 32 or not x_aster_admin_key or not hmac.compare_digest(expected, x_aster_admin_key): raise HTTPException(403, "Admin authorization required")
    deposits = dbs.execute(select(DepositIntent.status, func.count(DepositIntent.id)).group_by(DepositIntent.status)).all()
    withdrawals = dbs.execute(select(WithdrawalRequest.status, func.count(WithdrawalRequest.id)).group_by(WithdrawalRequest.status)).all()