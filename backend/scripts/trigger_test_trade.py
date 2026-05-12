import asyncio
import os
import sys
from sqlalchemy.orm import Session

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.core.factory import ServiceFactory
from app.models.risk_state import RiskState
from app.models.exchange_credential import ExchangeCredential
from app.core.encryption import decrypt
from app.services.exchange import ExchangeService
from app.core.logging import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger("trigger_test_trade")

async def trigger_trade():
    """
    Triggers a manual market order on the demo account to test 
    the full execution pipeline, database logging, and UI visibility.
    """
    db = SessionLocal()
    try:
        print("\n" + "="*50)
        print(" APEX BOT: MANUAL TRADE TRIGGER (BYBIT DEMO)")
        print("="*50)

        # 1. Fetch Demo Credentials
        print("[*] Fetching demo credentials from database...")
        cred = db.query(ExchangeCredential).filter_by(profile="demo").first()
        if not cred or not cred.api_key:
            print("ERROR: Demo credentials not found or incomplete in database.")
            return

        # 2. Initialize Exchange Service with Demo Keys
        print("[*] Initializing Exchange Service with Demo credentials...")
        is_demo_url = cred.base_url and "api-demo.bybit.com" in cred.base_url
        
        demo_exchange = ExchangeService(
            api_key=decrypt(cred.api_key),
            api_secret=decrypt(cred.api_secret),
            testnet=(not is_demo_url), 
            base_url=cred.base_url
        )
        
        # 3. Initialize Orchestrator with forced Demo Exchange
        print("[*] Setting up Orchestrator...")
        factory = ServiceFactory(db)
        factory.exchange = demo_exchange
        ServiceFactory._instance = factory
        
        orchestrator = ServiceFactory.get_orchestrator(db)
        
        # 4. Prepare Risk State
        risk_state = db.query(RiskState).first()
        original_live_state = risk_state.is_live_enabled if risk_state else False
        
        print(f"[*] Original RiskState.is_live_enabled: {original_live_state}")
        print("[*] Temporarily enabling live execution mode for this trigger...")
        if risk_state:
            risk_state.is_live_enabled = True
            db.commit()
        
        # 5. Configure Trade Parameters
        symbol = "BTC/USDT:USDT" 
        side = "BUY"
        leverage = 5
        target_usd = 5000.0
        
        print(f"[*] Fetching current price for {symbol}...")
        ticker = await demo_exchange.get_ticker(symbol)
        current_price = ticker['last']
        
        # Calculate amount: target_usd / current_price
        amount = round(target_usd / current_price, 3) 
        if amount <= 0: amount = 0.001 # Fallback
        
        print(f"[*] Targeting Symbol: {symbol} @ ${current_price:,.2f}")
        print(f"[*] Side: {side}")
        print(f"[*] Target USD: ${target_usd}")
        print(f"[*] Calculated Amount: {amount}")
        print(f"[*] Leverage: {leverage}x")
        
        # 6. Execute Order
        print("\n[>] Sending order to Bybit Demo...")
        order = await orchestrator.executor.open_position(
            symbol=symbol,
            side=side,
            amount=amount,
            order_type="MARKET",
            leverage=leverage,
            reasoning="MANUAL TEST TRIGGER: Verifying end-to-end execution pipeline (Analysis, Logging, UI)."
        )

        if order:
            print("\n" + "!"*50)
            print(" SUCCESS: POSITION OPENED SUCCESSFULLY")
            print(f" Order ID: {order.exchange_order_id}")
            price_val = f"${order.average_filled_price:,.2f}" if order.average_filled_price else "PENDING (Check UI)"
            print(f" Entry Price: {price_val}")
            print(f" Status: {order.status}")
            print("!"*50)
            print("\nCheck the Dashboard 'Positions' and 'Activity Log' to verify visibility.")
        else:
            print("\n" + "x"*50)
            print(" FAILURE: Order could not be placed.")
            print(" Check backend logs for detailed error information.")
            print("x"*50)

    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore original risk state
        if 'risk_state' in locals() and risk_state:
            print("\n[*] Restoring original risk state...")
            risk_state.is_live_enabled = original_live_state
            db.commit()
            
        # Clean up
        if 'demo_exchange' in locals():
            await demo_exchange.close()
        db.close()
        print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(trigger_trade())
