"""
Nightly Trainer Script.

Trains the PPO model on historical candles from ALL configured trading symbols
(BTC, ETH, SOL by default). One env is built per symbol so the policy learns
coin-specific patterns via the symbol one-hot in the state vector.
"""

import asyncio
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.learning.trading_environment import TradingEnvironment
from app.services.learning.reward import RewardFunction
from app.services.learning.state_space import StateSpace
from app.models.order import Order
from app.core.config import settings
from app.core.logging import get_logger
from stable_baselines3 import PPO

logger = get_logger(__name__)


def _model_dim_matches(model_path: str, expected_dim: int) -> bool:
    """Return True if the saved model's observation shape == expected_dim. False on any error."""
    try:
        tmp = PPO.load(model_path)
        shape = tmp.observation_space.shape
        return shape == (expected_dim,)
    except Exception:
        return False


async def _train_on_symbol(symbol: str, model_path: str, steps_per_symbol: int = 5000):
    """Build env for one symbol and run incremental learning on the shared model."""
    from app.services.market_data import MarketDataService
    from app.core.factory import ServiceFactory

    db = SessionLocal()
    try:
        factory = ServiceFactory(db)
        market = MarketDataService(factory.exchange)

        historical_data = await market.get_candles(
            symbol=symbol,
            timeframe="1h",
            limit=1000,
        )
        if not historical_data:
            logger.warning("no_historical_data_for_symbol", symbol=symbol)
            return False

        env = TradingEnvironment(historical_data=historical_data, symbol=symbol)
        expected_dim = env.observation_space.shape[0]

        # Load model only if dim matches; else start fresh
        if os.path.exists(model_path + ".zip") and _model_dim_matches(model_path, expected_dim):
            logger.info("loading_existing_model", path=model_path + ".zip", symbol=symbol)
            model = PPO.load(model_path, env=env)
        else:
            if os.path.exists(model_path + ".zip"):
                logger.warning("model_dim_mismatch_recreating", expected=expected_dim, path=model_path)
                try:
                    os.remove(model_path + ".zip")
                except OSError as e:
                    logger.warning("model_remove_failed", error=str(e))
            logger.info("creating_new_model", symbol=symbol, obs_dim=expected_dim)
            model = PPO("MlpPolicy", env, verbose=0)

        logger.info("training_steps_start", steps=steps_per_symbol, symbol=symbol)
        model.learn(total_timesteps=steps_per_symbol)
        model.save(model_path)
        logger.info("symbol_training_completed", symbol=symbol, path=model_path)
        return True
    finally:
        db.close()


async def run_nightly_training():
    """Iterate every configured symbol; train and persist one shared multi-symbol model."""
    logger.info("nightly_training_started")
    db = SessionLocal()
    try:
        models_dir = os.path.join(os.getcwd(), "models")
        os.makedirs(models_dir, exist_ok=True)
        model_path = os.path.join(models_dir, "apex_ppo_latest")

        symbols = settings.get_symbol_list()
        if not symbols:
            logger.warning("no_symbols_configured_for_training")
            return

        trained = []
        for sym in symbols:
            try:
                ok = await _train_on_symbol(sym, model_path)
                if ok:
                    trained.append(sym)
            except Exception as e:
                logger.error("symbol_training_failed", symbol=sym, error=str(e))

        if not trained:
            logger.warning("no_symbols_trained_skipping_audit")
            return

        from app.services.audit_log import log_audit
        log_audit(
            db=db,
            user="SYSTEM",
            action="model_training",
            details={
                "model_path": model_path,
                "symbols": trained,
                "reasoning": f"Nightly RL training on {len(trained)} symbol(s): {', '.join(trained)}",
                "cycles": 1,
            },
        )
        logger.info("nightly_training_completed", path=model_path, symbols=trained)

    except Exception as e:
        logger.error("nightly_training_failed", error=str(e))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_nightly_training())
