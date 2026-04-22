"""
Initialization script for TimescaleDB.
Creates hypertables and sets retention policies.
"""

from sqlalchemy import text
from app.core.database import engine, Base
from app.models.candle import Candle
from app.core.logging import get_logger

logger = get_logger(__name__)

def init_timescale_db():
    """Menginisialisasi TimescaleDB hypertable."""
    # 1. Pastikan tabel standar sudah terbuat
    Base.metadata.create_all(bind=engine)
    logger.info("standard_tables_created")

    with engine.connect() as conn:
        # 2. Cek apakah TimescaleDB extension sudah ada
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            conn.commit()
            logger.info("timescaledb_extension_ensured")
        except Exception as e:
            logger.warning("timescaledb_extension_failed", error=str(e))
            # Mungkin DB-nya tidak support extension, lanjut saja sebagai tabel biasa

        # 3. Ubah tabel candles menjadi hypertable
        try:
            # Perlu transaction commit yang benar untuk raw SQL
            conn.execute(text("SELECT create_hypertable('candles', 'timestamp', if_not_exists => TRUE);"))
            conn.commit()
            logger.info("candle_hypertable_created")
        except Exception as e:
            logger.warning("create_hypertable_failed", error=str(e))

        # 4. Tambahkan retention policy (Opsional, sesuaikan dengan kebutuhan)
        # Hapus data yang lebih tua dari 90 hari
        try:
            conn.execute(text("SELECT add_retention_policy('candles', INTERVAL '90 days', if_not_exists => TRUE);"))
            conn.commit()
            logger.info("retention_policy_added")
        except Exception as e:
            logger.warning("retention_policy_failed", error=str(e))

        # 5. Integration Logs Hypertable & Retention (30 days)
        try:
            conn.execute(text("SELECT create_hypertable('integration_logs', 'timestamp', if_not_exists => TRUE);"))
            conn.execute(text("SELECT add_retention_policy('integration_logs', INTERVAL '30 days', if_not_exists => TRUE);"))
            conn.commit()
            logger.info("integration_logs_retention_policy_added")
        except Exception as e:
            logger.warning("integration_logs_retention_failed", error=str(e))

        # 5. Initialize RiskState if missing
        from app.models.risk_state import RiskState
        from sqlalchemy.orm import Session
        db = Session(bind=engine)
        try:
            state = db.query(RiskState).first()
            if not state:
                state = RiskState(
                    current_equity=0.0,
                    system_status="NORMAL",
                    is_live_enabled=False
                )
                db.add(state)
                db.commit()
                logger.info("risk_state_initialized")
        except Exception as e:
            logger.error("risk_state_init_failed", error=str(e))
        finally:
            db.close()

if __name__ == "__main__":
    init_timescale_db()
