# Epic 4: Multi-Agent Core — Analyst Agents

---

## T-4.1: Implementasi Technical Analyst Agent

**Labels:** `epic-4`, `agent`, `technical-analysis`, `priority-critical`
**Milestone:** Fase 2 — Brain

### Deskripsi
Membuat agent yang menganalisa pergerakan harga menggunakan indikator teknikal. Agent ini membaca data candlestick dan menghitung berbagai indikator, lalu menyerahkan interpretasinya ke AI untuk menghasilkan sinyal trading.

### Apa itu Analisa Teknikal?
Analisa teknikal memprediksi arah harga berdasarkan **pola harga masa lalu**. Asumsinya: "Sejarah cenderung berulang." Contoh: Jika harga menyentuh garis support 5 kali dan selalu memantul naik, kemungkinan besar akan memantul naik lagi.

### Indikator yang Diimplementasikan

| Indikator | Kegunaan | Sinyal |
|---|---|---|
| **RSI (14)** | Overbought/Oversold | RSI > 70 = overbought (jual), RSI < 30 = oversold (beli) |
| **MACD** | Trend & momentum | MACD cross di atas signal = bullish, di bawah = bearish |
| **Bollinger Bands (20,2)** | Volatilitas & range | Harga di luar band atas = overbought, bawah = oversold |
| **EMA (9, 21, 50, 200)** | Trend direction | EMA pendek di atas EMA panjang = uptrend |
| **Fibonacci Retracement** | Level support/resistance | Level 38.2%, 50%, 61.8% sebagai area potensial bounce |
| **Volume Profile** | Volume di setiap harga | Area high-volume = support/resistance kuat |
| **ATR (14)** | Ukuran volatilitas | ATR tinggi = market bergejolak, perlu SL lebih lebar |
| **Ichimoku Cloud** | Trend + S/R + momentum | Harga di atas cloud = bullish, di bawah = bearish |

### Langkah-Langkah Implementasi

#### 1. Install dependencies
```bash
pip install pandas ta-lib numpy
# Atau jika ta-lib sulit diinstall:
pip install pandas-ta numpy
echo "pandas>=2.2.0" >> backend/requirements.txt
echo "pandas-ta>=0.3.14b" >> backend/requirements.txt
echo "numpy>=1.26.0" >> backend/requirements.txt
```

#### 2. Buat file `backend/app/agents/technical.py`

```python
"""
Technical Analyst Agent.

Menganalisa data harga menggunakan indikator teknikal dan menghasilkan
sinyal trading (BUY/SELL/HOLD) dengan confidence score.

Usage:
    agent = TechnicalAnalystAgent(ai_provider)
    signal = await agent.analyze("BTC/USDT", candles_data)
"""

import pandas as pd
import pandas_ta as ta
from typing import Any
from app.core.ai_provider import AIProvider, ChatMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


# Standardized output schema
class AgentSignal:
    """Output standar dari setiap agent."""
    def __init__(
        self,
        agent_name: str,
        signal: str,        # "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL"
        confidence: float,  # 0.0 - 1.0
        reasoning: str,     # Penjelasan mengapa sinyal ini
        metadata: dict = None,  # Data pendukung (indikator values, dll)
    ):
        self.agent_name = agent_name
        self.signal = signal
        self.confidence = confidence
        self.reasoning = reasoning
        self.metadata = metadata or {}


class TechnicalAnalystAgent:
    """Agent yang menganalisa data harga secara teknikal."""

    AGENT_NAME = "technical_analyst"

    # System prompt yang menjelaskan siapa agent ini
    SYSTEM_PROMPT = """You are an expert Technical Analyst for cryptocurrency markets.
You analyze price data using technical indicators and produce trading signals.

Your analysis must be:
1. Data-driven — base your signal ONLY on the indicators provided
2. Multi-timeframe — consider alignment across timeframes
3. Conservative — when in doubt, signal NEUTRAL
4. Specific — state exact indicator values that support your conclusion

Output MUST be valid JSON with this structure:
{
    "signal": "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL",
    "confidence": 0.0 to 1.0,
    "reasoning": "explanation in 2-3 sentences",
    "key_levels": {
        "support": [price1, price2],
        "resistance": [price1, price2]
    },
    "indicators_summary": {
        "trend": "bullish" | "bearish" | "neutral",
        "momentum": "bullish" | "bearish" | "neutral",
        "volatility": "high" | "normal" | "low"
    }
}"""

    def __init__(self, ai_provider: AIProvider):
        self.ai = ai_provider

    def calculate_indicators(self, df: pd.DataFrame) -> dict:
        """
        Hitung semua indikator teknikal dari data candlestick.
        
        Args:
            df: DataFrame dengan kolom: open, high, low, close, volume
        
        Returns:
            Dict berisi nilai semua indikator
        """
        indicators = {}

        # RSI (Relative Strength Index)
        df["rsi"] = ta.rsi(df["close"], length=14)
        indicators["rsi"] = round(df["rsi"].iloc[-1], 2)

        # MACD
        macd = ta.macd(df["close"])
        indicators["macd"] = {
            "macd_line": round(macd.iloc[-1, 0], 4),
            "signal_line": round(macd.iloc[-1, 1], 4),
            "histogram": round(macd.iloc[-1, 2], 4),
        }

        # Bollinger Bands
        bbands = ta.bbands(df["close"], length=20, std=2)
        indicators["bollinger"] = {
            "upper": round(bbands.iloc[-1, 0], 2),
            "middle": round(bbands.iloc[-1, 1], 2),
            "lower": round(bbands.iloc[-1, 2], 2),
            "current_price": round(df["close"].iloc[-1], 2),
        }

        # EMA (Exponential Moving Averages)
        for period in [9, 21, 50, 200]:
            ema = ta.ema(df["close"], length=period)
            indicators[f"ema_{period}"] = round(ema.iloc[-1], 2) if not pd.isna(ema.iloc[-1]) else None

        # ATR (Average True Range)
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        indicators["atr"] = round(df["atr"].iloc[-1], 2)

        # Volume (current vs average)
        indicators["volume"] = {
            "current": df["volume"].iloc[-1],
            "avg_20": round(df["volume"].tail(20).mean(), 2),
            "above_average": df["volume"].iloc[-1] > df["volume"].tail(20).mean(),
        }

        # Current price
        indicators["current_price"] = round(df["close"].iloc[-1], 2)

        return indicators

    async def analyze(
        self,
        symbol: str,
        candles_by_timeframe: dict[str, list[dict]],
    ) -> AgentSignal:
        """
        Analisa teknikal lengkap pada satu trading pair.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            candles_by_timeframe: Dict dari MarketDataService.get_multi_timeframe_candles()
        
        Returns:
            AgentSignal dengan sinyal, confidence, dan reasoning
        """
        # Step 1: Hitung indikator untuk setiap timeframe
        all_indicators = {}
        for tf, candles in candles_by_timeframe.items():
            df = pd.DataFrame(candles)
            all_indicators[tf] = self.calculate_indicators(df)

        # Step 2: Kirim ke AI untuk interpretasi
        data_str = f"Symbol: {symbol}\n\nIndicators by Timeframe:\n"
        for tf, indicators in all_indicators.items():
            data_str += f"\n=== {tf.upper()} ===\n{indicators}\n"

        instruction = (
            f"Analyze the technical indicators for {symbol} across all timeframes. "
            f"Identify trend alignment, divergences, and key levels. "
            f"Produce a trading signal with confidence score."
        )

        response = await self.ai.analyze(
            system_prompt=self.SYSTEM_PROMPT,
            data=data_str,
            instruction=instruction,
            json_mode=True,
        )

        # Step 3: Parse response AI
        import json
        result = json.loads(response.content)

        signal = AgentSignal(
            agent_name=self.AGENT_NAME,
            signal=result["signal"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            metadata={
                "indicators": all_indicators,
                "key_levels": result.get("key_levels", {}),
                "indicators_summary": result.get("indicators_summary", {}),
            },
        )

        logger.info("technical_analysis_completed",
            symbol=symbol,
            signal=signal.signal,
            confidence=signal.confidence,
        )

        return signal
```

### Definition of Done
- [ ] Semua 8 indikator teknikal dihitung dengan benar
- [ ] Multi-timeframe analysis berfungsi (15m, 1h, 4h, 1d)
- [ ] AI menginterpretasi indikator dan menghasilkan sinyal JSON
- [ ] Output berupa `AgentSignal` yang terstruktur
- [ ] Unit test: input data → indikator dihitung → sinyal dihasilkan

### File yang Dibuat
- `[NEW]` `backend/app/agents/technical.py`
- `[NEW]` `backend/tests/test_technical_agent.py`

---

## T-4.2: Multi-Timeframe Analysis pada Technical Agent

**Labels:** `epic-4`, `agent`, `technical-analysis`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-4.1

### Deskripsi
Meningkatkan Technical Agent agar bisa mendeteksi **alignment** (keselarasan) sinyal antar timeframe. Trade yang paling menguntungkan biasanya terjadi saat sinyal di semua timeframe sejalan.

### Konsep Multi-Timeframe
- **Timeframe besar (1D, 4H):** Menentukan arah TREND utama
- **Timeframe kecil (1H, 15m):** Menentukan TIMING entry

Contoh ideal: 1D = uptrend, 4H = uptrend, 1H = pullback ke support → **BUY** (masuk saat koreksi dalam tren naik).

### Langkah-Langkah
1. Tambah method `_detect_tf_alignment()` di `TechnicalAnalystAgent`
2. Scoring: sinyal boost +20% confidence jika semua TF sejalan, -30% jika TF besar berlawanan
3. Tambahkan ke sistem prompt agar AI mempertimbangkan alignment
4. Output metadata harus menyertakan alignment status

### Definition of Done
- [ ] Alignment detection berfungsi
- [ ] Confidence diboost saat TF sejalan
- [ ] Confidence dikurangi saat TF berlawanan
- [ ] AI mempertimbangkan alignment dalam reasoning

---

## T-4.3: Implementasi Fundamental Analyst Agent

**Labels:** `epic-4`, `agent`, `fundamental-analysis`, `priority-critical`
**Milestone:** Fase 2 — Brain
**Depends On:** T-3.4, T-3.5

### Deskripsi
Membuat agent yang menganalisa faktor fundamental — berita, data on-chain, dan event ekonomi. Agent ini TIDAK melihat grafik harga (itu tugas Technical Agent), melainkan melihat "cerita" di balik pergerakan harga.

### Input yang Diterima Agent
1. **Berita terbaru** (dari T-3.5) — apakah ada berita major? regulasi? hack?
2. **Data on-chain** (dari T-3.4) — whale movement, exchange flow
3. **Event kalender** — FOMC meeting, Bitcoin halving, major token unlock

### Langkah-Langkah
1. Buat `backend/app/agents/fundamental.py`
2. System prompt: "You are a Cryptocurrency Fundamental Analyst..."
3. Agent menerima data berita, on-chain, dan event
4. Proses: kirim data mentah → AI menginterpretasi dampaknya ke harga
5. Output: `AgentSignal` (sama seperti Technical Agent)
6. Punya `importance_weight`: berita regulasi lebih berat dari berita minor

### Definition of Done
- [ ] Agent menerima dan menganalisa berita kripto
- [ ] Agent menerima dan menginterpretasi data on-chain
- [ ] AI menghasilkan sinyal bullish/bearish berdasarkan fundamental
- [ ] Output format sama: `AgentSignal`

### File yang Dibuat
- `[NEW]` `backend/app/agents/fundamental.py`

---

## T-4.4: Implementasi Sentiment Analyst Agent

**Labels:** `epic-4`, `agent`, `sentiment-analysis`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-3.6

### Deskripsi
Membuat agent yang mengukur "mood" pasar. Berbeda dari fundamental (yang melihat fakta/berita), sentiment melihat **perasaan dan perilaku** pelaku pasar.

### Input
| Data | Interpretasi |
|---|---|
| Fear & Greed Index < 20 | Extreme Fear → biasanya waktu beli (contrarian) |
| Fear & Greed Index > 80 | Extreme Greed → biasanya hati-hati (contrarian) |
| Funding Rate sangat positif | Terlalu banyak Long → koreksi mungkin terjadi |
| Funding Rate negatif | Short dominan → potensi short squeeze (harga naik tajam) |
| Open Interest naik + harga naik | Trend kuat |
| Open Interest turun + harga turun | Likuidasi massal |

### Langkah-Langkah
1. Buat `backend/app/agents/sentiment.py`
2. System prompt khusus sentiment analysis
3. Agent menerima data sentimen (Fear & Greed, Funding Rate, Open Interest, Long/Short Ratio)
4. AI menginterpretasi kombinasi data menjadi sinyal
5. Output: `AgentSignal` (format standar)

### Definition of Done
- [ ] Agent mengolah semua data sentimen dari T-3.6
- [ ] Interpretasi contrarian dipertimbangkan (extreme fear = buy)
- [ ] Output format standar `AgentSignal`

### File yang Dibuat
- `[NEW]` `backend/app/agents/sentiment.py`

---

## T-4.5: Implementasi Risk Manager Agent

**Labels:** `epic-4`, `agent`, `risk-management`, `priority-critical`
**Milestone:** Fase 2 — Brain

### Deskripsi
Membuat agent yang bertugas sebagai "polisi" — mengevaluasi apakah suatu trade LAYAK dieksekusi berdasarkan kondisi portfolio saat ini. Agent ini memiliki wewenang untuk **MENOLAK** trade meskipun semua agent lain setuju.

### Apa yang Dievaluasi?
1. **Current exposure:** Sudah berapa persen modal yang digunakan?
2. **Open positions:** Apakah sudah terlalu banyak posisi terbuka?
3. **Correlation:** Apakah trade baru ini berkorelasi dengan posisi yang sudah ada?
4. **Drawdown status:** Apakah sedang dalam periode rugi?
5. **Position sizing:** Berapa besar ukuran posisi yang diperbolehkan?

### Output Risk Manager
Berbeda dari agent lain, Risk Manager output-nya:
```json
{
    "decision": "APPROVE" | "REJECT" | "REDUCE_SIZE",
    "max_position_size_usd": 500.0,
    "max_leverage": 5,
    "reasoning": "Current exposure is 15%. Max is 20%. Approved with reduced size.",
    "risk_metrics": {
        "current_exposure_pct": 15.0,
        "daily_pnl_pct": -1.2,
        "open_positions_count": 3,
        "max_correlation": 0.85
    }
}
```

### Langkah-Langkah
1. Buat `backend/app/agents/risk_manager.py`
2. Implementasi kalkulasi: exposure, correlation, drawdown
3. Rules engine: hardcoded rules + AI reasoning
4. TIDAK BOLEH hanya AI — rules keamanan harus hardcoded (AI bisa salah, rules tidak)

### Definition of Done
- [ ] Risk Manager bisa APPROVE, REJECT, atau REDUCE_SIZE
- [ ] Position sizing dikalkulasi berdasarkan balance & exposure
- [ ] Hardcoded safety rules TIDAK bisa di-override oleh AI
- [ ] Drawdown check berfungsi
- [ ] Correlation check antar posisi berfungsi

### File yang Dibuat
- `[NEW]` `backend/app/agents/risk_manager.py`

---

## T-4.6: Standarisasi Output Format Semua Agent

**Labels:** `epic-4`, `architecture`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-4.1 s/d T-4.5

### Deskripsi
Memastikan semua agent mengeluarkan output dalam format yang **persis sama** (`AgentSignal`). Ini penting agar Consensus Engine (Epic 5) bisa mengolah sinyal dari semua agent secara seragam.

### Langkah-Langkah
1. Finalisasi `AgentSignal` schema sebagai Pydantic model di `backend/app/schemas/agent_signal.py`
2. Pastikan setiap agent mereturn `AgentSignal` — tidak ada exception
3. Jika agent gagal analisis, return `AgentSignal(signal="NEUTRAL", confidence=0.0, reasoning="Analysis failed: ...")`
4. Tambahkan field `timestamp` untuk tracking kapan sinyal dihasilkan

### Definition of Done
- [ ] `AgentSignal` schema final dan digunakan semua agent
- [ ] Tidak ada agent yang return format berbeda
- [ ] Error di agent menghasilkan NEUTRAL signal (bukan crash)

### File yang Dibuat
- `[NEW]` `backend/app/schemas/agent_signal.py`

---

## T-4.7: Prompt Engineering & Testing untuk Setiap Agent

**Labels:** `epic-4`, `ai-core`, `testing`, `priority-high`
**Milestone:** Fase 2 — Brain
**Depends On:** T-4.1 s/d T-4.6

### Deskripsi
Mengoptimasi system prompt untuk setiap agent agar menghasilkan sinyal yang akurat dan konsisten. Ini adalah proses iteratif — prompt diuji, dievaluasi, dan ditingkatkan berkali-kali.

### Langkah-Langkah
1. Siapkan 10 skenario test data real (historis):
   - 3 skenario bullish clear
   - 3 skenario bearish clear
   - 2 skenario sideways
   - 2 skenario volatile/choppy
2. Jalankan setiap agent dengan data tersebut
3. Evaluasi: apakah sinyal sesuai dengan yang diharapkan?
4. Iterate prompt hingga accuracy ≥ 70% pada test set
5. Simpan prompt terbaik dalam `backend/app/agents/prompts/` sebagai file terpisah

### Definition of Done
- [ ] Setiap agent diuji dengan 10 skenario
- [ ] Accuracy ≥ 70% pada test set
- [ ] Prompt final disimpan di folder `prompts/`
- [ ] Laporan hasil testing terdokumentasi

---

## T-4.8: Unit Test & Backtesting Masing-Masing Agent

**Labels:** `epic-4`, `testing`, `priority-high`
**Milestone:** Fase 2 — Brain

### Deskripsi
Membuat unit test untuk memastikan setiap agent berfungsi dengan benar, dan backtesting sederhana untuk mengukur akurasi sinyal masing-masing agent terhadap data historis.

### Langkah-Langkah
1. Unit test: input data mock → agent menghasilkan `AgentSignal` valid
2. Unit test: input data kosong/invalid → agent return NEUTRAL (bukan error)
3. Backtesting sederhana:
   - Ambil 3 bulan data historis BTC/USDT
   - Jalankan agent setiap 4 jam
   - Bandingkan sinyal agent vs yang sebenarnya terjadi
   - Hitung accuracy per agent

### Definition of Done
- [ ] Unit test semua agent pass
- [ ] Backtesting minimal 3 bulan data
- [ ] Accuracy report per agent terdokumentasi
- [ ] Edge cases tertangani (data kosong, API error, etc.)

### File yang Dibuat
- `[NEW]` `backend/tests/test_technical_agent.py`
- `[NEW]` `backend/tests/test_fundamental_agent.py`
- `[NEW]` `backend/tests/test_sentiment_agent.py`
- `[NEW]` `backend/tests/test_risk_manager_agent.py`
