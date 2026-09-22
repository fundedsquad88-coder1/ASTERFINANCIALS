"""Run the Aster blockchain watcher continuously.

Usage:
    python -m app.blockchain_worker

Configure RPC/API credentials through environment variables. The worker is
safe to restart because every transfer is deduplicated by transaction hash
(and BSC log index is included in the stored unique key).
"""
import logging
import os
import time

from app.blockchain import scan_once
from app.main import SessionLocal

logging.basicConfig(level=os.getenv("ASTER_LOG_LEVEL","INFO"))
log=logging.getLogger("aster.blockchain")

def main():
    interval=max(5,int(os.getenv("ASTER_BLOCKCHAIN_POLL_SECONDS","15")))
    while True:
        dbs=SessionLocal()
        try:
            result=scan_once(dbs)
            log.info("blockchain scan: %s",result)
        except Exception:
            dbs.rollback()
            log.exception("blockchain scan failed")
        finally:
            dbs.close()
        time.sleep(interval)

if __name__=="__main__":
    main()
