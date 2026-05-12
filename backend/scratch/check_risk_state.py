from app.core.database import SessionLocal
from app.models.risk_state import RiskState

db = SessionLocal()
try:
    risk_state = db.query(RiskState).first()
    if risk_state:
        print(f"System Status: {risk_state.system_status}")
        print(f"Is Live Enabled: {risk_state.is_live_enabled}")
        print(f"Current Equity: {risk_state.current_equity}")
    else:
        print("RiskState table is empty.")
finally:
    db.close()
