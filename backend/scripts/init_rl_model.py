"""
Initialize Base RL Model.

Script ini membuat model PPO dasar (untrained) untuk pertama kali
agar sistem memiliki file 'brain' awal di folder persistent.
"""

import os
import torch
from stable_baselines3 import PPO
from app.services.learning.trading_environment import TradingEnvironment

def init_base_model():
    print("🚀 Initializing Base RL Model...")
    
    # 1. Setup path
    # Di dalam kontainer pathnya adalah /app/models
    models_dir = os.path.join(os.getcwd(), "models")
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "apex_ppo_latest")
    
    # 2. Create a dummy environment for initialization
    # (Hanya untuk mendefinisikan space observasi dan aksi)
    # Kita gunakan data dummy karena ini hanya inisialisasi arsitektur
    dummy_data = [
        {"timestamp": 0, "open": 60000, "high": 61000, "low": 59000, "close": 60500, "volume": 100}
        for _ in range(100)
    ]
    env = TradingEnvironment(historical_data=dummy_data)
    
    # 3. Create Model
    print("🧠 Creating PPO model with MlpPolicy...")
    model = PPO("MlpPolicy", env, verbose=1)
    
    # 4. Save Model
    print(f"💾 Saving model to {model_path}.zip...")
    model.save(model_path)
    
    print("✅ Base RL Model initialized successfully!")
    print("Bot sekarang akan memuat model ini saat restart.")

if __name__ == "__main__":
    init_base_model()
