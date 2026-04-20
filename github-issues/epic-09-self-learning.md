# Epic 9: Self-Learning & Reinforcement Learning Engine

---

## T-9.1: Desain Reward Function untuk RL

**Labels:** `epic-9`, `self-learning`, `reinforcement-learning`, `priority-critical`
**Milestone:** Fase 4 — Intelligence

### Deskripsi
Mendefinisikan **reward function** — formula yang memberi "hadiah" atau "hukuman" kepada bot setelah setiap trade. Ini adalah inti dari self-learning: bot belajar dari reward yang diterima.

### Desain Reward Function

```python
def calculate_reward(trade_result: dict) -> float:
    """
    Hitung reward setelah trade ditutup.
    
    Komponen reward:
    1. Profit/Loss (utama)
    2. Risk-adjusted return (Sharpe-like)
    3. Bonus/penalty untuk perilaku tertentu
    """
    reward = 0.0
    
    # === Komponen 1: Profit/Loss (bobot 60%) ===
    pnl_pct = trade_result["pnl_percentage"]
    reward += pnl_pct * 0.6
    
    # === Komponen 2: Risk-Adjusted (bobot 25%) ===
    # Bonus jika profit dengan risk rendah
    risk_ratio = trade_result["pnl"] / trade_result["max_risk"]  # Actual P/L dibagi risiko SL
    reward += min(risk_ratio, 3.0) * 0.25  # Cap di 3x untuk hindari outlier
    
    # === Komponen 3: Behavioral Bonus/Penalty (bobot 15%) ===
    # Bonus: Mengikuti risk rules
    if trade_result["had_stop_loss"]:
        reward += 0.05  # Selalu pasang SL
    
    # Bonus: Mengambil partial profit
    if trade_result["partial_close_count"] > 0:
        reward += 0.03
    
    # Penalty: Trading melawan trend utama
    if trade_result["against_main_trend"]:
        reward -= 0.10
    
    # Penalty: Terlalu sering trade (overtrading)
    if trade_result["time_held_minutes"] < 5:
        reward -= 0.15  # Hukuman berat untuk scalping < 5 menit
    
    # === Komponen 4: HOLD reward ===
    # Memberi reward kecil untuk TIDAK trading saat kondisi buruk
    if trade_result.get("action") == "HOLD" and trade_result.get("market_was_bad"):
        reward += 0.02  # Reward karena menghindari trade buruk
    
    return reward
```

### Mengapa Reward Function Penting?
Ini yang membedakan bot pintar dari bot bodoh. Reward function yang buruk akan mengajarkan perilaku buruk (misalnya: selalu YOLO tanpa SL karena kadang profit besar). Reward function yang baik mengajarkan konsistensi dan manajemen risiko.

### Definition of Done
- [ ] Reward function terdefinisi dengan 4 komponen
- [ ] Profit dikalkulasi dengan risk-adjustment
- [ ] Behavioral bonus/penalty diterapkan
- [ ] HOLD reward ada (tidak hanya menghargai trade)
- [ ] Reward cap untuk mencegah outlier
- [ ] Unit test dengan berbagai skenario trade

### File yang Dibuat
- `[NEW]` `backend/app/services/learning/reward.py`
- `[NEW]` `backend/app/services/learning/__init__.py`

---

## T-9.2: State Space Representation

**Labels:** `epic-9`, `self-learning`, `reinforcement-learning`, `priority-critical`
**Milestone:** Fase 4 — Intelligence

### Deskripsi
Mendefinisikan **state space** — representasi numerik dari kondisi pasar dan portfolio saat ini. State inilah yang "dilihat" oleh RL agent untuk membuat keputusan.

### Komponen State Vector

```python
state = {
    # === Market Indicators (dari Technical Agent) ===
    "rsi_15m": 45.2,
    "rsi_1h": 52.1,
    "rsi_4h": 60.3,
    "macd_histogram_1h": 0.002,
    "bb_position_1h": 0.6,        # 0=lower band, 0.5=middle, 1=upper
    "ema_trend_alignment": 0.8,    # 1=all bullish, -1=all bearish
    "atr_normalized": 1.2,         # 1=normal, >1.5=high volatility
    
    # === Sentiment ===
    "fear_greed_index": 45,
    "funding_rate": 0.001,
    "long_short_ratio": 1.5,
    
    # === Portfolio State ===
    "current_exposure_pct": 0.15,  # 15% modal terpakai
    "open_positions_count": 2,
    "unrealized_pnl_pct": 0.02,   # +2% floating profit
    "daily_pnl_pct": -0.005,       # -0.5% hari ini
    "consecutive_losses": 1,
    
    # === Market Regime ===
    "regime": 0,  # 0=trending_up, 1=trending_down, 2=sideways, 3=volatile
    
    # === Copy Trading Signal ===
    "top_trader_consensus": 0.6,  # 60% top trader sedang long
}
```

### Langkah-Langkah
1. Buat `backend/app/services/learning/state.py`
2. Method `build_state_vector(market_data, portfolio, agents)` → numpy array
3. Normalisasi semua nilai ke range [0, 1] atau [-1, 1]
4. Total dimensi state: ~20-30 features
5. Pastikan state representatif tapi tidak terlalu besar (curse of dimensionality)

### Definition of Done
- [ ] State vector terdefinisi dengan 20-30 features
- [ ] Semua nilai ter-normalisasi
- [ ] Method `build_state_vector()` mengembalikan numpy array
- [ ] Bisa di-serialize/deserialize untuk penyimpanan

### File yang Dibuat
- `[NEW]` `backend/app/services/learning/state.py`

---

## T-9.3: RL Training Pipeline (PPO/TD3)

**Labels:** `epic-9`, `self-learning`, `reinforcement-learning`, `priority-critical`
**Milestone:** Fase 4 — Intelligence
**Depends On:** T-9.1, T-9.2

### Deskripsi
Implementasi training pipeline menggunakan Proximal Policy Optimization (PPO). Bot belajar dari pengalaman trading-nya untuk memperbaiki keputusan di masa depan.

### Apa itu PPO?
PPO adalah algoritma RL yang belajar dari trial-and-error. Bayangkan anak kecil belajar berjalan: jatuh → sakit (negative reward) → coba cara lain → berhasil → senang (positive reward). PPO melakukan ini secara matematis dan cepat.

### Langkah-Langkah

#### 1. Install dependency
```bash
pip install stable-baselines3 gymnasium
echo "stable-baselines3>=2.3.0" >> backend/requirements.txt
echo "gymnasium>=0.29.0" >> backend/requirements.txt
```

#### 2. Buat custom Gym environment
```python
# backend/app/services/learning/trading_env.py

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class TradingEnvironment(gym.Env):
    """
    Custom Gym environment untuk training RL agent.
    
    State: Market indicators + portfolio state (dari T-9.2)
    Actions: BUY, SELL, HOLD, INCREASE, DECREASE
    Reward: Risk-adjusted PnL (dari T-9.1)
    """
    
    def __init__(self, historical_data, initial_balance=10000):
        super().__init__()
        
        self.data = historical_data
        self.initial_balance = initial_balance
        
        # Action space: 5 discrete actions
        self.action_space = spaces.Discrete(5)
        # 0=HOLD, 1=BUY, 2=SELL, 3=INCREASE, 4=DECREASE
        
        # Observation space: state vector dimension
        self.observation_space = spaces.Box(
            low=-1, high=1,
            shape=(25,),  # 25 features
            dtype=np.float32
        )
        
        self.reset()
    
    def reset(self, seed=None, options=None):
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = None
        self.total_reward = 0
        return self._get_state(), {}
    
    def step(self, action):
        # 1. Execute action
        # 2. Calculate reward
        # 3. Check if done
        # 4. Return new state, reward, done, info
        ...
```

#### 3. Training script
```python
from stable_baselines3 import PPO

# Create environment
env = TradingEnvironment(historical_data)

# Create model
model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
)

# Train
model.learn(total_timesteps=100_000)

# Save
model.save("models/apex_rl_v1")
```

### Definition of Done
- [ ] Custom Gym environment berfungsi
- [ ] PPO model bisa di-train tanpa error
- [ ] Model bisa di-save dan di-load
- [ ] Training reward meningkat seiring waktu (learning curve positif)
- [ ] Model bisa menghasilkan action dari state

### File yang Dibuat
- `[NEW]` `backend/app/services/learning/trading_env.py`
- `[NEW]` `backend/app/services/learning/trainer.py`

---

## T-9.4: Setup ChromaDB sebagai Pattern Memory

**Labels:** `epic-9`, `self-learning`, `vector-database`, `priority-high`
**Milestone:** Fase 4 — Intelligence

### Deskripsi
Setup ChromaDB sebagai "memori jangka panjang" bot. Di sini bot menyimpan "sidik jari" kondisi pasar saat trade sukses/gagal, sehingga bisa mengenali pola serupa di masa depan.

### Analogi
Seperti anda yang menghafal: "Terakhir kali jalan ini macet jam 5 sore, jadi besok saya lewat jalan lain." Bot menghafal: "Terakhir kali RSI 80 + volume turun + sentiment negatif → saya BUY dan rugi. Jadi sekarang kondisi mirip, saya HOLD."

### Langkah-Langkah
1. Buat `backend/app/services/learning/pattern_memory.py`
2. Koneksi ke ChromaDB (sudah di-setup via Docker di T-1.3)
3. Collection "trade_patterns" untuk menyimpan embedding
4. Method `store_pattern(trade_context, outcome)` → simpan embedding
5. Method `find_similar(current_context, top_k=5)` → cari pola serupa
6. Metadata per pattern: outcome (win/loss), pnl%, market regime, timestamp

### Definition of Done
- [ ] ChromaDB terkoneksi dan collection dibuat
- [ ] Pattern bisa disimpan (store)
- [ ] Pattern serupa bisa dicari (similarity search)
- [ ] Metadata outcome tersimpan

### File yang Dibuat
- `[NEW]` `backend/app/services/learning/pattern_memory.py`

---

## T-9.5: Trade Outcome Embedding

**Labels:** `epic-9`, `self-learning`, `priority-high`
**Milestone:** Fase 4 — Intelligence
**Depends On:** T-9.4

### Deskripsi
Setiap kali trade ditutup, buat "sidik jari" (embedding) dari kondisi market saat trade terjadi, lalu simpan ke Pattern Memory beserta hasilnya (win/loss).

### Langkah-Langkah
1. Setelah trade close, kumpulkan snapshot: semua indikator teknikal, sentimen, regime, agent signals
2. Convert snapshot ke text description
3. Gunakan AI embedding model untuk convert ke vector
4. Simpan ke ChromaDB: vector + metadata (outcome, pnl_pct, regime, timestamp)

### Definition of Done
- [ ] Setiap closed trade menghasilkan embedding
- [ ] Embedding + metadata tersimpan di ChromaDB
- [ ] Bisa di-query: "Cari 5 trade paling mirip dengan kondisi saat ini"

---

## T-9.6: Similarity Search untuk Decision Support

**Labels:** `epic-9`, `self-learning`, `priority-high`
**Milestone:** Fase 4 — Intelligence
**Depends On:** T-9.5

### Deskripsi
Sebelum membuat keputusan baru, cari kondisi serupa di Pattern Memory. Jika kondisi serupa di masa lalu menghasilkan rugi → confidence trade turun. Jika menghasilkan profit → confidence naik.

### Langkah-Langkah
1. Saat Orchestrator akan membuat keputusan, panggil Pattern Memory
2. Cari top 5 pola paling mirip
3. Hitung win rate dari 5 pola tersebut
4. Jika win rate > 60% → boost confidence +10%
5. Jika win rate < 40% → reduce confidence -15%
6. Masukkan info historis ke reasoning Orchestrator

### Definition of Done
- [ ] Similarity search berjalan sebelum setiap keputusan
- [ ] Confidence adjustment berdasarkan historical patterns
- [ ] Reasoning menyertakan referensi historis

---

## T-9.7: Agent Performance Scoring

**Labels:** `epic-9`, `self-learning`, `priority-critical`
**Milestone:** Fase 4 — Intelligence

### Deskripsi
Sistem scoring untuk mengukur akurasi masing-masing agent. Agent yang sering benar mendapat skor tinggi, yang sering salah mendapat skor rendah.

### Mekanisme Scoring
Setelah setiap trade:
```python
for agent_name, signal in trade_decision.agent_signals.items():
    if signal.signal in ["BUY", "STRONG_BUY"] and trade_pnl > 0:
        # Agent bilang BUY dan memang profit → BENAR
        await agent_scorer.update(agent_name, reward=+1)
    elif signal.signal in ["SELL", "STRONG_SELL"] and trade_pnl < 0:
        # Agent bilang SELL dan memang turun → BENAR
        await agent_scorer.update(agent_name, reward=+1)
    elif signal.signal == "NEUTRAL":
        # Agent menahan diri → reward kecil
        await agent_scorer.update(agent_name, reward=+0.1)
    else:
        # Agent salah prediksi → penalty
        await agent_scorer.update(agent_name, reward=-1)
```

### Langkah-Langkah
1. Implementasi di `backend/app/services/agent_scorer.py` (foundation di T-5.4)
2. Tabel DB: agent_name, total_score, total_evaluations, accuracy, last_updated
3. Accuracy = correct_predictions / total_predictions
4. Score menggunakan EMA (Exponential Moving Average) agar recent performance lebih berbobot
5. Dashboard panel menampilkan skor ini

### Definition of Done
- [ ] Setiap agent mendapat skor setelah setiap trade
- [ ] Accuracy ter-hitung
- [ ] Score menggunakan EMA (bukan simple average)
- [ ] Data tersimpan di database

---

## T-9.8: Automatic Agent Weight Adjustment

**Labels:** `epic-9`, `self-learning`, `priority-high`
**Milestone:** Fase 4 — Intelligence
**Depends On:** T-9.7

### Deskripsi
Bobot voting setiap agent di Consensus Engine otomatis berubah berdasarkan skor performanya. Agent paling akurat mendapat bobot terbesar.

### Langkah-Langkah
1. Convert scores ke weights menggunakan softmax:
```python
import numpy as np

def scores_to_weights(scores: dict[str, float]) -> dict[str, float]:
    names = list(scores.keys())
    values = np.array([scores[n] for n in names])
    
    # Softmax normalization
    exp_values = np.exp(values - np.max(values))
    weights = exp_values / exp_values.sum()
    
    # Apply minimum floor (0.05)
    weights = np.maximum(weights, 0.05)
    weights = weights / weights.sum()  # Re-normalize
    
    return dict(zip(names, weights))
```
2. Update weights di Consensus Engine setiap setelah scoring
3. Log perubahan weight di database

### Definition of Done
- [ ] Weight otomatis berubah berdasarkan skor
- [ ] Minimum floor (0.05) diterapkan
- [ ] Log perubahan weight

---

## T-9.9: Strategy Versioning

**Labels:** `epic-9`, `self-learning`, `priority-high`
**Milestone:** Fase 4 — Intelligence

### Deskripsi
Setiap kali strategi berubah (weight update, RL model update), simpan sebagai versi baru. Ini memungkinkan rollback ke versi sebelumnya jika performa turun.

### Apa yang Di-version?
1. Agent weights
2. RL model checkpoint
3. Consensus threshold
4. Regime-based parameters

### Langkah-Langkah
1. Buat `backend/app/services/learning/strategy_version.py`
2. Setiap perubahan: snapshot semua parameter → simpan sebagai version
3. Format: `v1_20260420`, `v2_20260421`, dst.
4. Simpan metadata: tanggal, alasan perubahan, metrics sebelum perubahan
5. Maximum 30 versions disimpan (auto-delete yang terlama)

### Definition of Done
- [ ] Setiap perubahan strategi disimpan sebagai version
- [ ] Metadata lengkap tersimpan
- [ ] Version bisa di-list dan di-restore
- [ ] Maximum 30 versions

### File yang Dibuat
- `[NEW]` `backend/app/services/learning/strategy_version.py`

---

## T-9.10: Auto-Rollback Strategy

**Labels:** `epic-9`, `self-learning`, `safety`, `priority-critical`
**Milestone:** Fase 4 — Intelligence
**Depends On:** T-9.9

### Deskripsi
Jika strategi baru menghasilkan performa buruk (win rate turun signifikan selama 3 hari berturut), otomatis rollback ke versi sebelumnya.

### Trigger Rollback
- Win rate 3 hari terakhir < win rate versi sebelumnya - 10%
- ATAU daily loss limit terkena 2x dalam 3 hari
- ATAU consecutive loss > 7

### Langkah-Langkah
1. Track daily performance metrics per strategy version
2. Bandingkan dengan versi sebelumnya
3. Jika trigger terpenuhi: rollback + notify
4. Alert Telegram: "Strategy v5 underperforming. Auto-rolled back to v4."

### Definition of Done
- [ ] Trigger rollback berfungsi
- [ ] Rollback otomatis ke versi sebelumnya
- [ ] Alert terkirim saat rollback
- [ ] Log rollback tercatat

---

## T-9.11: Incremental Nightly Training

**Labels:** `epic-9`, `self-learning`, `scheduler`, `priority-high`
**Milestone:** Fase 4 — Intelligence
**Depends On:** T-9.3

### Deskripsi
Setiap malam (02:00 WIB, saat aktivitas rendah), jalankan training incremental menggunakan data trade hari itu. Ini berbeda dari training dari nol — model lama di-update dengan pengalaman baru (fine-tuning).

### Langkah-Langkah
1. CRON job daily pukul 02:00 WIB
2. Kumpulkan semua trade data hari itu
3. Load model RL saat ini
4. Train tambahan 10,000 timesteps dengan data baru
5. Evaluate model baru vs model lama (pada test set)
6. Jika model baru lebih baik → simpan sebagai versi baru
7. Jika model baru lebih buruk → buang, tetap pakai model lama

### Definition of Done
- [ ] Nightly training berjalan otomatis
- [ ] Model lama tidak hilang (versioning)
- [ ] Model baru hanya di-adopt jika lebih baik
- [ ] Training selesai dalam < 30 menit

---

## T-9.12: Self-Learning Dashboard Metrics

**Labels:** `epic-9`, `dashboard`, `priority-medium`
**Milestone:** Fase 4 — Intelligence

### Deskripsi
Menyediakan endpoint API untuk menampilkan metrik self-learning di dashboard:
- Agent scores timeline (grafik skor per agent dari waktu ke waktu)
- Strategy version log (daftar versi + performa masing-masing)
- RL training metrics (reward curve)
- Pattern memory stats (jumlah patterns, similar pattern hits)

### Definition of Done
- [ ] Endpoint REST tersedia
- [ ] Data akurat dan ter-update
- [ ] Bisa divisualisasi sebagai grafik di dashboard
