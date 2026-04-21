"""
Nightly Trainer Script.

Menjalankan training incremental untuk model RL setiap malam 
menggunakan data trade terbaru.
"""

import asyncio
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.learning.trading_environment import TradingEnvironment
from app.services.learning.reward import RewardFunction
from app.models.order import Order
from app.core.logging import get_logger
from stable_baselines3 import PPO

logger = get_logger(__name__)

async def run_nightly_training():
    """
    1. Kumpulkan data trade hari ini.
    2. Jalankan fine-tuning pada model RL.
    3. Simpan checkpoint.
    """
    logger.info("nightly_training_started")
    db = SessionLocal()
    
    try:
        # (Simulasi: Ambil data historis dari API atau DB untuk training)
        # Dalam prod: Ini akan fetch real market data
        mock_data = [{"close": 50000 + i*10, "high": 50100, "low": 49900} for i in range(1000)]
        
        env = TradingEnvironment(historical_data=mock_data)
        
        model_path = "./models/apex_ppo_latest"
        if os.path.exists(model_path + ".zip"):
            logger.info("loading_existing_model")
            model = PPO.load(model_path, env=env)
        else:
            logger.info("creating_new_model")
            model = PPO("MlpPolicy", env, verbose=1)
            
        # 4. Incremental training
        logger.info("training_steps_start", steps=10000)
        model.learn(total_timesteps=10000)
        
        # 5. Save model
        os.makedirs("./models", exist_ok=True)
        model.save(model_path)
        logger.info("nightly_training_completed", path=model_path)
        
    except Exception as e:
        logger.error("nightly_training_failed", error=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_nightly_training())
