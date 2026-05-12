"""
Trading Environment for RL.

Custom Gymnasium Environment untuk melatih agent Reinforcement Learning.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, List
from app.services.learning.state_space import StateSpace
from app.schemas.portfolio import PortfolioState

class TradingEnvironment(gym.Env):
    """
    Environment untuk melatih bot trading.
    Menggunakan StateSpace nyata untuk menghasilkan observasi dari data historis.
    
    Actions: 0=HOLD, 1=BUY/LONG, 2=SELL/SHORT
    """
    
    def __init__(self, historical_data: List[Dict[str, Any]], initial_balance: float = 10000, symbol: str = "BTC/USDT:USDT"):
        super().__init__()

        self.data = historical_data
        self.initial_balance = initial_balance
        self.symbol = symbol
        # Use StateSpace default — auto-sized to base + coin one-hot
        self.state_service = StateSpace()
        feature_dim = self.state_service.feature_dim

        # 0=HOLD, 1=LONG, 2=SHORT
        self.action_space = spaces.Discrete(3)

        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(feature_dim,),
            dtype=np.float32
        )

        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 25 # Start with enough data for lookback
        self.balance = self.initial_balance
        self.position = None # None, "LONG", "SHORT"
        self.entry_price = 0.0
        
        state = self._get_observation()
        return state, {}

    def step(self, action):
        """
        Jalankan 1 langkah simulasi.
        """
        if self.current_step >= len(self.data) - 1:
            return self._get_observation(), 0.0, True, False, {}

        current_data = self.data[self.current_step]
        current_price = getattr(current_data, 'close', current_data.get('close', 0) if isinstance(current_data, dict) else 0)
        
        reward = 0.0
        terminated = False
        
        # 1. Execute action
        pnl_pct = 0.0
        if action == 1: # LONG
            if self.position == "SHORT":
                pnl_pct = (self.entry_price - current_price) / self.entry_price * 100
                self.balance *= (1 + (pnl_pct / 100))
                self.position = None
            if self.position is None:
                self.position = "LONG"
                self.entry_price = current_price
        
        elif action == 2: # SHORT
            if self.position == "LONG":
                pnl_pct = (current_price - self.entry_price) / self.entry_price * 100
                self.balance *= (1 + (pnl_pct / 100))
                self.position = None
            if self.position is None:
                self.position = "SHORT"
                self.entry_price = current_price
        
        # 2. Advance step
        self.current_step += 1
        if self.current_step >= len(self.data) - 1:
            terminated = True

        # 3. Calculate Reward using RewardFunction
        from app.services.learning.reward import RewardFunction
        reward_service = RewardFunction()
        reward = reward_service.calculate({
            "pnl_pct": pnl_pct,
            "max_drawdown_during_trade": 0.0, # Simulation detail
            "had_sl": True, # Assume SL is always used in training for now
            "hold_time_minutes": 60 # Assume 1h candles
        })
            
        # 3. Get next observation
        obs = self._get_observation()
        
        return obs, reward, terminated, False, {}

    def _get_observation(self) -> np.ndarray:
        """
        Membangun state vector nyata dari jendela data historis.
        """
        lookback = 20
        start_idx = max(0, self.current_step - lookback)
        window = self.data[start_idx : self.current_step + 1]
        
        # Simulated portfolio state for the RL agent during training
        portfolio = PortfolioState(
            total_balance=self.initial_balance,
            total_equity=self.balance,
            available_margin=self.balance if self.position is None else 0.0,
            open_positions=[],
            daily_pnl_pct=0.0,
            weekly_pnl_pct=0.0,
            max_drawdown_pct=0.0
        )
        
        # Simulate market_data structure for StateSpace
        market_data = {
            "candles": {"1h": window},
            "fear_greed_index": 50
        }
        
        # Simulate agent signals for RL input (RL learns to weight these)
        agent_signals = {
            "technical": "NEUTRAL",
            "fundamental": "NEUTRAL",
            "sentiment": "NEUTRAL"
        }
        
        return self.state_service.build_vector(market_data, portfolio, agent_signals, symbol=self.symbol)
