from app.core.database import SessionLocal
from app.models.integration_log import IntegrationLog
from sqlalchemy import desc

db = SessionLocal()
try:
    logs = db.query(IntegrationLog).order_by(desc(IntegrationLog.timestamp)).limit(10).all()
    if logs:
        print(f"{'Timestamp':<25} | {'Service':<15} | {'Provider':<10} | {'Endpoint':<15} | {'Status':<10} | {'Latency':<5}")
        print("-" * 100)
        for log in logs:
            print(f"{str(log.timestamp):<25} | {log.service_type:<15} | {log.provider_name:<10} | {log.endpoint:<15} | {log.status:<10} | {log.latency_ms:<5}ms")
    else:
        print("No integration logs found.")
finally:
    db.close()
