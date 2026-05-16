from app.core.database import SessionLocal
from app.models.system_settings import SystemSettings

db = SessionLocal()
current = SystemSettings.get_value(db, "trading_symbols")
print(f"Current DB trading_symbols: {current}")

if current:
    symbols = [s.strip() for s in current.split(",") if s.strip()]
    if "XRP/USDT:USDT" not in symbols:
        symbols.append("XRP/USDT:USDT")
        SystemSettings.set_value(db, "trading_symbols", ",".join(symbols))
        print("Updated DB with XRP/USDT:USDT")
    else:
        print("XRP already in DB.")
else:
    print("trading_symbols not set in DB, fallback to config.py will be used.")

db.close()
