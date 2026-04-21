"""
Trading Environment for RL.

Custom Gymnasium Environment untuk melatih agent Reinforcement Learning.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, List
from app.services.learning.state_space import StateSpace

class TradingEnvironment(gym.Env):
    """
    Environment untuk melatih bot trading.
    
    Actions: 0=HOLD, 1=BUY/LONG, 2=SELL/SHORT
    Observations: State vector dari StateSpace service.
    """
    
    def __init__(self, historical_data: List[Dict[str, Any]], initial_balance: float = 10000):
        super().__init__()
        
        self.data = historical_data
        self.initial_balance = initial_balance
        self.state_service = StateSpace(feature_dim=25)
        
        # 0=HOLD, 1=LONG, 2=SHORT
        self.action_space = spaces.Discrete(3)
        
        # 25 features normalized to [-1, 1]
        self.observation_space = spaces.Box(
            low=-1.0, 
            high=1.0, 
            shape=(25,), 
            dtype=np.float32
        )
        
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = None # None, "LONG", "SHORT"
        self.entry_price = 0.0
        
        # Initial exploration: kumpulkan state pertama
        state = self._get_observation()
        return state, {}

    def step(self, action):
        """
        Jalankan 1 langkah simulasi.
        """
        # (LOGIKA SIMPLIFIED UNTUK TRAINING FAST)
        current_data = self.data[self.current_step]
        current_price = current_data["close"]
        
        reward = 0.0
        terminated = False
        
        # 1. Execute action
        if action == 1: # LONG
            if self.position == "SHORT":
                # Close short first
                pnl = (self.entry_price - current_price) / self.entry_price
                reward += pnl * 100
                self.position = None
            if self.position is None:
                self.position = "LONG"
                self.entry_price = current_price
        
        elif action == 2: # SHORT
            if self.position == "LONG":
                # Close long first
                pnl = (current_price - self.entry_price) / self.entry_price
                reward += pnl * 100
                self.position = None
            if self.position is None:
                self.position = "SHORT"
                self.entry_price = current_price
        
        # Action 0 = HOLD: reward kecil jika market flat, atau bias holding if win
        
        # 2. Advance step
        self.current_step += 1
        if self.current_step >= len(self.data) - 1:
            terminated = True
            
        # 3. Get next observation
        obs = self._get_observation()
        
        return obs, reward, terminated, False, {}

    def _get_observation(self) -> np.ndarray:
        # (Mocking data for env speed during training)
        # Dalam prod, ini akan memanggil StateSpace dengan data asli
        return np.random.uniform(-1, 1, (25,)).astype(np.float32)
