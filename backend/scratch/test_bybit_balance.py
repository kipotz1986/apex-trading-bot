import asyncio
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv

async def test_balance():
    from app.core.database import SessionLocal
    from app.models.exchange_credential import ExchangeCredential
    from app.core.encryption import decrypt
    
    db = SessionLocal()
    profile = db.query(ExchangeCredential).filter_by(profile="demo").first()
    db.close()
    
    if not profile:
        print("No demo profile found in DB")
        return
        
    api_key = decrypt(profile.api_key)
    api_secret = decrypt(profile.api_secret)
    testnet = True # Demo is always testnet in our logic
    
    print(f"Testing with API Key from DB: {api_key[:5]}...")
    
    exchange = ccxt.bybit({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',
        }
    })
    
    if testnet:
        exchange.set_sandbox_mode(True)
        
    try:
        balance = await exchange.fetch_balance()
        import json
        print("\n--- Full Balance (JSON) ---")
        # Mask keys if necessary, but this is a test script
        print(json.dumps(balance, indent=2))
        
        print("\n--- Summary ---")
        if 'info' in balance and 'result' in balance['info'] and 'list' in balance['info']['result']:
            unified_data = balance['info']['result']['list'][0]
            print(f"Total Equity (Info): {unified_data.get('totalEquity')}")
            print(f"Total Wallet Balance (Info): {unified_data.get('totalWalletBalance')}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_balance())
