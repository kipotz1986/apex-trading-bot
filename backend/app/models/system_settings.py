from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime
from datetime import datetime
from app.core.database import Base

class SystemSettings(Base):
    """Store system-wide configuration and risk parameters."""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True) # e.g., "daily_loss_limit"
    value = Column(String) # Store as string, cast on use
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_value(cls, db, key, default=None):
        item = db.query(cls).filter(cls.key == key).first()
        return item.value if item else default

    @classmethod
    def set_value(cls, db, key, value):
        item = db.query(cls).filter(cls.key == key).first()
        if item:
            item.value = str(value)
        else:
            item = cls(key=key, value=str(value))
            db.add(item)
        db.commit()

    @classmethod
    def seed_defaults(cls, db):
        """Seed default values for keys that don't yet exist in the DB."""
        defaults = {
            "daily_loss_limit": "3.0",
            "weekly_loss_limit": "7.0",
            "max_drawdown_pct": "15.0",
            "max_leverage": "10",
            "max_position_size": "5.0",
            "max_total_exposure": "80.0",
            "consecutive_loss_limit": "5",
            "consecutive_loss_multiplier": "0.5",
            "paper_trial_days": "14",
            "min_trade_size_usd": "10.0",
            "consensus_threshold_strong": "0.7",
            "consensus_threshold_moderate": "0.4",
            "advanced_reasoning_enabled": "false",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
        }
        for key, value in defaults.items():
            if not db.query(cls).filter(cls.key == key).first():
                db.add(cls(key=key, value=value))
        db.commit()
