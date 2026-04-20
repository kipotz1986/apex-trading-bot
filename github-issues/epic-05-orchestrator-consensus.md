# Epic 5: Master Orchestrator & Consensus Engine

---

## T-5.1: Implementasi Master Orchestrator Agent

**Labels:** `epic-5`, `agent`, `orchestrator`, `priority-critical`
**Milestone:** Fase 2 — Brain
**Depends On:** T-4.1 s/d T-4.6

### Deskripsi
Membuat Master Orchestrator — "otak pusat" yang mengkoordinasi seluruh agent. Ia menerima sinyal dari semua agent (Technical, Fundamental, Sentiment, Risk Manager, Copy Trader), menjalankan consensus, dan mengeluarkan keputusan final: EXECUTE atau HOLD.

### Analogi
Bayangkan rapat direksi perusahaan. Setiap direktur (agent) menyampaikan pendapatnya. CEO (Orchestrator) mendengar semua, mempertimbangkan, lalu mengambil keputusan final.

### Langkah-Langkah Implementasi

#### 1. Buat `backend/app/agents/orchestrator.py`

```python
"""
Master Orchestrator Agent.

Mengkoordinasi semua agent, menjalankan consensus voting,
dan menghasilkan keputusan final trading.

Flow:
1. Kumpulkan sinyal dari semua agent
2. Jalankan weighted voting (Consensus Engine)
3. Jika ada konflik tajam, jalankan Debate Protocol
4. Cek Risk Manager approval
5. Hasilkan keputusan final: EXECUTE atau HOLD

Usage:
    orchestrator = MasterOrchestrator(ai_provider, agents, consensus_engine)
    decision = await orchestrator.decide("BTC/USDT", market_data)
"""

from dataclasses import dataclass
from typing import Optional
from app.agents.technical import TechnicalAnalystAgent
from app.agents.fundamental import FundamentalAnalystAgent
from app.agents.sentiment import SentimentAnalystAgent
from app.agents.risk_manager import RiskManagerAgent
from app.agents.copy_trader import CopyTradingAgent
from app.schemas.agent_signal import AgentSignal
from app.core.ai_provider import AIProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TradeDecision:
    """Keputusan final dari Orchestrator."""
    action: str         # "EXECUTE_LONG" | "EXECUTE_SHORT" | "CLOSE" | "HOLD"
    symbol: str
    confidence: float
    position_size_usd: float
    stop_loss: Optional[float] = None
    take_profit: list[float] = None  # Multi-level TP
    leverage: int = 1
    reasoning: str = ""
    agent_signals: dict = None  # Rekaman sinyal setiap agent
    consensus_score: float = 0.0


class MasterOrchestrator:
    """Koordinator utama semua agent."""

    def __init__(
        self,
        ai_provider: AIProvider,
        technical_agent: TechnicalAnalystAgent,
        fundamental_agent: FundamentalAnalystAgent,
        sentiment_agent: SentimentAnalystAgent,
        risk_manager: RiskManagerAgent,
        copy_trader: CopyTradingAgent,
        consensus_engine,  # dari T-5.2
    ):
        self.ai = ai_provider
        self.technical = technical_agent
        self.fundamental = fundamental_agent
        self.sentiment = sentiment_agent
        self.risk_manager = risk_manager
        self.copy_trader = copy_trader
        self.consensus = consensus_engine

    async def decide(self, symbol: str, market_data: dict) -> TradeDecision:
        """
        Proses pengambilan keputusan trading.
        
        Args:
            symbol: Trading pair
            market_data: Semua data pasar yang dibutuhkan agent
        
        Returns:
            TradeDecision — keputusan final
        """
        # Step 1: Kumpulkan sinyal dari semua agent (paralel)
        import asyncio
        signals = await asyncio.gather(
            self.technical.analyze(symbol, market_data["candles"]),
            self.fundamental.analyze(symbol, market_data["news"], market_data["onchain"]),
            self.sentiment.analyze(symbol, market_data["sentiment"]),
            self.copy_trader.analyze(symbol),
            return_exceptions=True,  # Jangan crash jika 1 agent gagal
        )

        # Handle agent failures — jadikan NEUTRAL
        processed_signals = {}
        agent_names = ["technical", "fundamental", "sentiment", "copy_trader"]
        for name, signal in zip(agent_names, signals):
            if isinstance(signal, Exception):
                logger.error(f"agent_{name}_failed", error=str(signal))
                processed_signals[name] = AgentSignal(
                    agent_name=name, signal="NEUTRAL",
                    confidence=0.0, reasoning=f"Agent failed: {signal}"
                )
            else:
                processed_signals[name] = signal

        # Step 2: Jalankan Consensus Engine
        consensus_result = self.consensus.calculate(processed_signals)

        # Step 3: Jika ada konflik, jalankan Debate Protocol
        if consensus_result.has_conflict:
            consensus_result = await self._debate_protocol(
                symbol, processed_signals, consensus_result
            )

        # Step 4: Cek Risk Manager
        risk_decision = await self.risk_manager.evaluate(
            symbol=symbol,
            proposed_action=consensus_result.action,
            proposed_size=consensus_result.position_size,
        )

        # Step 5: Final decision
        if risk_decision.decision == "REJECT":
            return TradeDecision(
                action="HOLD",
                symbol=symbol,
                confidence=consensus_result.confidence,
                position_size_usd=0,
                reasoning=f"Ditolak Risk Manager: {risk_decision.reasoning}",
                agent_signals=processed_signals,
                consensus_score=consensus_result.score,
            )

        actual_size = min(
            consensus_result.position_size,
            risk_decision.max_position_size_usd
        )

        return TradeDecision(
            action=consensus_result.action,
            symbol=symbol,
            confidence=consensus_result.confidence,
            position_size_usd=actual_size,
            stop_loss=consensus_result.stop_loss,
            take_profit=consensus_result.take_profits,
            leverage=min(consensus_result.leverage, risk_decision.max_leverage),
            reasoning=consensus_result.reasoning,
            agent_signals=processed_signals,
            consensus_score=consensus_result.score,
        )
```

### Definition of Done
- [ ] Orchestrator mengumpulkan sinyal dari semua agent
- [ ] Jika 1 agent gagal, proses tetap berjalan (graceful degradation)
- [ ] Consensus engine dipanggil setelah semua sinyal terkumpul
- [ ] Risk Manager memiliki hak veto (bisa tolak trade)
- [ ] Output berupa `TradeDecision` yang lengkap
- [ ] Semua sinyal agent disimpan dalam decision (untuk audit trail)

### File yang Dibuat
- `[NEW]` `backend/app/agents/orchestrator.py`
- `[NEW]` `backend/app/schemas/trade_decision.py`

---

## T-5.2: Implementasi Consensus Engine — Weighted Voting

**Labels:** `epic-5`, `agent`, `consensus`, `priority-critical`
**Milestone:** Fase 2 — Brain

### Deskripsi
Membuat engine yang menghitung konsensus dari sinyal semua agent melalui **weighted voting** (voting terbobot). Setiap agent memiliki bobot yang berbeda dan bisa berubah seiring waktu berdasarkan track record mereka.

### Cara Kerja

```
Final Score = Σ (signal_value × confidence × agent_weight)

signal_value mapping:
  STRONG_BUY  = +1.0
  BUY         = +0.5
  NEUTRAL     =  0.0
  SELL        = -0.5
  STRONG_SELL = -1.0

Contoh:
  Technical (weight=0.30):  BUY, confidence=80%  → +0.5 × 0.8 × 0.30 = +0.120
  Fundamental (weight=0.25): NEUTRAL, conf=50%   →  0.0 × 0.5 × 0.25 =  0.000
  Sentiment (weight=0.20):  BUY, confidence=70%  → +0.5 × 0.7 × 0.20 = +0.070
  Copy Trader (weight=0.25): STRONG_BUY, conf=90% → +1.0 × 0.9 × 0.25 = +0.225
  
  Total = 0.415 → 41.5% (di bawah 70% threshold → HOLD)
```

### Langkah-Langkah
1. Buat `backend/app/services/consensus.py`
2. Implementasi signal-to-numeric conversion
3. Implementasi weighted sum calculation
4. Threshold: `≥ 0.70` → EXECUTE, `0.40–0.69` → WEAK (bisa debate), `< 0.40` → HOLD
5. Detect conflict: jika ada agent STRONG_BUY dan agent lain STRONG_SELL
6. Return `ConsensusResult` dengan score, action, has_conflict

### Definition of Done
- [ ] Weighted voting berfungsi dengan bobot dinamis
- [ ] Threshold decision berfungsi (EXECUTE/WEAK/HOLD)
- [ ] Conflict detection berfungsi
- [ ] Unit test dengan berbagai skenario voting

### File yang Dibuat
- `[NEW]` `backend/app/services/consensus.py`

---

## T-5.3: Implementasi Debate Protocol

**Labels:** `epic-5`, `agent`, `consensus`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-5.2

### Deskripsi
Ketika agent-agent berkonflik (misalnya Technical = STRONG_BUY tapi Fundamental = STRONG_SELL), sistem menjalankan "debat" di mana masing-masing agent menjelaskan alasannya, lalu AI sebagai judge memutuskan.

### Flow Debate
1. Identifikasi agent yang berkonflik
2. Minta setiap agent menjelaskan reasoning-nya lebih detail (memperkuat argumen)
3. Kirim semua argumen ke Master AI (judge)
4. Judge mempertimbangkan semua argumen + konteks historis
5. Judge menghasilkan keputusan akhir + reasoning

### Langkah-Langkah
1. Tambah method `_debate_protocol()` di orchestrator
2. System prompt untuk judge: "You are a senior trading strategist arbitrating..."
3. Judge HARUS menyebut argumen mana yang lebih kuat dan mengapa
4. Output: updated `ConsensusResult` dengan confidence yang sudah di-adjust

### Definition of Done
- [ ] Debate hanya terjadi saat ada konflik tajam antar agent
- [ ] Judge menerima argumen dari semua pihak
- [ ] Keputusan judge disertai penjelasan yang logis
- [ ] Hasil debate tercatat di decision log

---

## T-5.4: Dynamic Agent Weighting

**Labels:** `epic-5`, `self-learning`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-5.2

### Deskripsi
Bobot voting setiap agent bukan statis — mereka berubah berdasarkan akurasi prediksi agent di masa lalu. Agent yang sering benar mendapat bobot lebih besar, yang sering salah bobotnya dikecilkan.

### Mekanisme
1. Setiap kali trade ditutup, evaluasi agent mana yang sinyalnya benar
2. Update skor agent: `score += reward` jika benar, `score -= penalty` jika salah
3. Convert skor ke bobot: `weight = softmax(scores)` agar total = 1.0
4. Simpan skor ke database
5. Minimum weight floor: 0.05 (agar agent tidak pernah 100% diabaikan)

### Langkah-Langkah
1. Buat `backend/app/services/agent_scorer.py`
2. Tabel database `agent_scores`: agent_name, score, weight, last_updated
3. Method `update_score()` dipanggil setelah setiap trade close
4. Method `get_weights()` dipanggil oleh Consensus Engine sebelum voting

### Definition of Done
- [ ] Agent scoring berfungsi (skor naik jika benar, turun jika salah)
- [ ] Bobot otomatis di-rebalance setiap ada update skor
- [ ] Data skor dan bobot disimpan di database
- [ ] Minimum weight floor (0.05) diterapkan
- [ ] Dashboard bisa menampilkan skor agent (untuk Epic 12)

### File yang Dibuat
- `[NEW]` `backend/app/services/agent_scorer.py`
- `[NEW]` `backend/app/models/agent_score.py`

---

## T-5.5: Implementasi Market Regime Detector

**Labels:** `epic-5`, `agent`, `market-analysis`, `priority-high`
**Milestone:** Fase 2 — Brain

### Deskripsi
Membuat modul yang mendeteksi kondisi pasar saat ini (Trending Up, Trending Down, Sideways, High Volatility). Ini penting karena strategi yang bagus di pasar trending bisa rugi besar di pasar sideways.

### 4 Regime Pasar

| Regime | Cara Deteksi | Contoh |
|---|---|---|
| **Trending Up** | EMA50 > EMA200, ADX > 25, Higher Highs | BTC naik dari $40k ke $70k bertahap |
| **Trending Down** | EMA50 < EMA200, ADX > 25, Lower Lows | BTC turun dari $70k ke $40k bertahap |
| **Sideways** | ADX < 20, harga dalam range sempit | BTC bolak-balik $60k-$65k selama 2 minggu |
| **High Volatility** | ATR melonjak 2x+ dari rata-rata, candle besar | BTC drop 10% dalam 1 hari karena berita |

### Langkah-Langkah
1. Buat `backend/app/services/regime_detector.py`
2. Gunakan ADX (Average Directional Index) untuk trend strength
3. Gunakan ATR untuk volatility
4. Gunakan EMA crossover untuk trend direction
5. Output: regime classification + confidence

### Definition of Done
- [ ] 4 regime terdeteksi dengan benar
- [ ] Confidence score untuk setiap klasifikasi
- [ ] Backtesting: cocokkan deteksi regime dengan kondisi historis yang diketahui

### File yang Dibuat
- `[NEW]` `backend/app/services/regime_detector.py`

---

## T-5.6: Regime-Based Behavior Switching

**Labels:** `epic-5`, `strategy`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-5.5

### Deskripsi
Mengubah perilaku bot berdasarkan regime pasar yang terdeteksi. Bot agresif saat trending, konservatif saat sideways, dan sangat defensif saat volatilitas tinggi.

### Konfigurasi per Regime

| Setting | Trending | Sideways | High Volatility |
|---|---|---|---|
| Confidence threshold | 60% | 80% | 90% |
| Max position size | 100% dari limit | 50% | 25% |
| Stop Loss distance | 1× ATR | 0.5× ATR | 2× ATR |
| Take Profit target | 3× ATR | 1× ATR | 2× ATR |
| Max leverage | 5x | 3x | 1x |
| New trades allowed | Yes | Limited | No (close-only) |

### Langkah-Langkah
1. Buat `backend/app/services/regime_strategy.py`
2. Definisikan parameter set untuk setiap regime (tabel di atas)
3. Orchestrator memanggil regime detector sebelum setiap keputusan
4. Parameter dari regime strategy menimpa default settings

### Definition of Done
- [ ] Setiap regime memiliki parameter set yang berbeda
- [ ] Orchestrator menggunakan parameter sesuai regime aktif
- [ ] Perubahan regime tercatat di log

---

## T-5.7: Integration Test — Full Pipeline

**Labels:** `epic-5`, `testing`, `priority-critical`
**Milestone:** Fase 2 — Brain
**Depends On:** T-5.1 s/d T-5.6

### Deskripsi
End-to-end test: dari data pasar masuk → semua agent menganalisis → consensus engine voting → orchestrator memutuskan → output TradeDecision yang valid.

### Skenario Test
1. **Semua agent setuju BUY** → Expected: EXECUTE_LONG
2. **Semua agent setuju SELL** → Expected: EXECUTE_SHORT
3. **Agent split (2 BUY, 2 SELL)** → Expected: HOLD atau Debate
4. **Risk Manager REJECT** → Expected: HOLD (meskipun consensus = BUY)
5. **Satu agent gagal (exception)** → Expected: tetap berjalan dengan agent lain
6. **Market regime = High Volatility** → Expected: threshold naik, posisi dikecilkan

### Definition of Done
- [ ] Semua 6 skenario berhasil
- [ ] Pipeline berjalan end-to-end tanpa error
- [ ] Waktu eksekusi < 30 detik per keputusan
- [ ] Semua data tercatat di log
