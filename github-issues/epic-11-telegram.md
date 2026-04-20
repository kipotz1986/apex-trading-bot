# Epic 11: Telegram Notification & Reporting

---

## T-11.1: Setup Telegram Bot via BotFather

**Labels:** `epic-11`, `telegram`, `setup`, `priority-high`
**Milestone:** Fase 5 — Interface

### Deskripsi
Membuat bot Telegram dan mengkonfigurasi koneksi dari aplikasi ke Telegram API. Bot ini akan mengirim laporan dan alert ke owner.

### Langkah-Langkah

#### 1. Buat bot Telegram
1. Buka @BotFather di Telegram
2. Kirim `/newbot`
3. Masukkan nama: `APEX Trading Bot`
4. Masukkan username: `apex_trading_XXXXX_bot` (harus unik)
5. Copy TOKEN yang diberikan BotFather

#### 2. Dapatkan Chat ID
1. Kirim pesan apapun ke bot yang baru dibuat
2. Buka di browser: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Cari `"chat":{"id":XXXXXXXXX}` — itu Chat ID Anda

#### 3. Simpan ke `.env`
```env
TELEGRAM_BOT_TOKEN=7000000000:AAHxxxxxxxxxxxxxxxxxxxxxxxxy
TELEGRAM_CHAT_ID=123456789
```

#### 4. Buat service `backend/app/services/telegram.py`

```python
"""
Telegram Notification Service.

Mengirim pesan, laporan, dan alert ke owner via Telegram.

Usage:
    telegram = TelegramService()
    await telegram.send_message("Hello from APEX!")
    await telegram.send_report(daily_report_data)
"""

import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


class TelegramService:
    """Service untuk komunikasi via Telegram."""

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.client = httpx.AsyncClient(timeout=30)

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
    ) -> bool:
        """
        Kirim pesan teks ke owner.
        
        Args:
            text: Isi pesan (support HTML formatting)
            parse_mode: "HTML" atau "Markdown"
            disable_notification: True = silent notification
        
        Returns:
            True jika berhasil terikirim
        """
        try:
            response = await self.client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_notification": disable_notification,
                },
            )
            data = response.json()
            
            if data.get("ok"):
                logger.info("telegram_message_sent", length=len(text))
                return True
            else:
                logger.error("telegram_send_failed", error=data)
                return False

        except Exception as e:
            logger.error("telegram_error", error=str(e))
            return False

    async def send_alert(self, level: str, title: str, body: str) -> bool:
        """
        Kirim alert dengan emoji sesuai level.
        
        level: "critical" | "warning" | "info" | "success"
        """
        emojis = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
            "success": "🟢",
        }
        
        emoji = emojis.get(level, "ℹ️")
        message = f"{emoji} <b>{title}</b>\n\n{body}"
        
        return await self.send_message(message)
```

### Definition of Done
- [ ] Bot Telegram dibuat dan token tersimpan di `.env`
- [ ] Chat ID tersimpan di `.env`
- [ ] `send_message()` berhasil mengirim pesan
- [ ] `send_alert()` berfungsi dengan berbagai level
- [ ] Error handling jika Telegram API down

### File yang Dibuat
- `[NEW]` `backend/app/services/telegram.py`

---

## T-11.2: Daily Report Composer

**Labels:** `epic-11`, `telegram`, `reporting`, `priority-high`
**Milestone:** Fase 5 — Interface
**Depends On:** T-11.1

### Deskripsi
Modul yang mengkompilasi data 24 jam terakhir menjadi laporan harian yang ringkas dan mudah dipahami (dalam bahasa Indonesia).

### Format Laporan

```
📊 APEX Daily Report — 20 April 2026

💰 Portfolio
• Balance: $10,250.00 (+2.5%)
• Equity: $10,180.00
• Unrealized PnL: -$70.00

📈 Kinerja 24 Jam
• Total Trade: 8
• Win / Loss: 5 / 3 (62.5%)
• Net Profit: +$250.00

🏆 Best Trade: BTC/USDT Long +$120.00 (+1.2%)
😓 Worst Trade: ETH/USDT Short -$45.00 (-0.9%)

📌 Open Positions (2)
• BTC/USDT Long | Entry $64,200 | PnL: +$30.00
• SOL/USDT Short | Entry $145.50 | PnL: -$100.00

🤖 AI Insight
Pasar BTC dalam trend naik moderat. Sentiment masih positif
dengan Fear & Greed di 65 (Greed). Strategi: tetap bullish
dengan trailing stop ketat.

⚙️ Bot Status: ✅ Running (Paper Mode)
Uptime: 72h | Strategy: v3 | Agent Accuracy: 68%
```

### Langkah-Langkah
1. Buat `backend/app/services/report_composer.py`
2. Query database: trades 24 jam, balance, open positions
3. Hitung metrik: win rate, net pnl, best/worst trade
4. Generate AI Insight (minta Master Orchestrator untuk ringkasan)
5. Format ke HTML/text untuk Telegram
6. Pastikan bahasa ringkas dan mudah dipahami non-trader

### Definition of Done
- [ ] Laporan terkompilasi otomatis dari data 24 jam
- [ ] Format jelas dan mudah dipahami
- [ ] AI Insight terintegrasi
- [ ] Terkirim tanpa error

### File yang Dibuat
- `[NEW]` `backend/app/services/report_composer.py`

---

## T-11.3: Scheduler CRON untuk Laporan Pukul 07:00 WIB

**Labels:** `epic-11`, `scheduler`, `priority-high`
**Milestone:** Fase 5 — Interface
**Depends On:** T-11.2

### Deskripsi
Mengimplementasikan scheduler yang memicu pengiriman laporan harian pada pukul 07:00 WIB (00:00 UTC) setiap hari tanpa gagal.

### Langkah-Langkah
1. Gunakan Celery Beat atau APScheduler
2. Schedule: `cron(hour=0, minute=0, timezone='Asia/Jakarta')` = 07:00 WIB
3. Job: `compose_daily_report()` → `send_telegram()`
4. Retry 3x jika gagal kirim (interval 5 menit)
5. Log setiap eksekusi (sukses/gagal)

### Implementasi APScheduler
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

scheduler.add_job(
    send_daily_report,
    trigger=CronTrigger(hour=7, minute=0, timezone="Asia/Jakarta"),
    id="daily_report",
    name="Daily Telegram Report",
    replace_existing=True,
)

scheduler.start()
```

### Definition of Done
- [ ] Laporan terkirim otomatis setiap pukul 07:00 WIB
- [ ] Retry jika gagal (max 3x)
- [ ] Log setiap eksekusi
- [ ] Timezone benar (WIB)

---

## T-11.4: Critical Alert System

**Labels:** `epic-11`, `telegram`, `alerting`, `priority-critical`
**Milestone:** Fase 5 — Interface
**Depends On:** T-11.1, Epic 8

### Deskripsi
Alert instan via Telegram untuk kejadian darurat. Ini BUKAN laporan harian — ini dikirim *saat itu juga* ketika sesuatu terjadi.

### Event yang Memicu Alert

| Event | Level | Contoh Pesan |
|---|---|---|
| Circuit breaker triggered | 🔴 Critical | "Daily loss limit reached: -3.2%. Bot paused." |
| Drawdown warning (10%) | 🟡 Warning | "Drawdown at 10.5%. Approaching 15% limit." |
| Drawdown emergency (15%) | 🔴 Critical | "Max drawdown reached. All positions closed. Bot stopped." |
| Big win (>2% single trade) | 🟢 Success | "BTC Long closed: +$500 (+2.5%)" |
| System error | ⚠️ Warning | "Exchange API connection lost. Retrying..." |
| Bot resumed | 🔵 Info | "Bot resumed trading after 24h pause." |

### Definition of Done
- [ ] Setiap event di tabel memicu alert yang sesuai
- [ ] Alert terkirim dalam < 30 detik
- [ ] Rate limiting: max 20 alert per jam (hindari spam)

---

## T-11.5: Per-Trade Notification (Opsional, Toggle-able)

**Labels:** `epic-11`, `telegram`, `priority-low`
**Milestone:** Fase 5 — Interface

### Deskripsi
Notifikasi setiap kali bot membuka atau menutup posisi. Fitur ini bisa di-toggle on/off oleh user di dashboard settings karena bisa cukup ramai.

### Format
```
📈 Position Opened
BTC/USDT LONG
Entry: $64,200.00
Size: $500.00 (5x leverage)
SL: $63,500.00 (-1.1%)
TP1: $64,850.00 (+1.0%)
TP2: $65,500.00 (+2.0%)
Confidence: 78%
```

### Definition of Done
- [ ] Notifikasi trade terkirim
- [ ] Bisa di-toggle on/off via settings
- [ ] Format jelas

---

## T-11.6: "AI Insight" Section

**Labels:** `epic-11`, `ai-core`, `reporting`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Deskripsi
Section dalam laporan harian yang berisi ringkasan kondisi pasar **dalam bahasa sederhana** yang bisa dipahami non-trader. Digenerate oleh AI.

### Langkah-Langkah
1. Kumpulkan: regime pasar, sinyal terakhir, top events, histori 24 jam
2. Kirim ke AI dengan prompt: "Jelaskan kondisi pasar saat ini dan rencana strategi dalam bahasa Indonesia sederhana. Penerima BUKAN trader. Gunakan maksimal 3 kalimat."
3. Sertakan dalam laporan harian

### Definition of Done
- [ ] AI insight di-generate setiap laporan
- [ ] Bahasa sederhana dan non-teknikal
- [ ] Maksimal 3-4 kalimat

---

## T-11.7: Bot Health Report

**Labels:** `epic-11`, `reporting`, `observability`, `priority-medium`
**Milestone:** Fase 5 — Interface

### Deskripsi
Section dalam laporan harian yang menampilkan "kesehatan" bot: uptime, error terakhir, versi strategi, dan progres learning.

### Data
- Uptime sejak terakhir restart
- Jumlah error dalam 24 jam
- Error terakhir (jika ada)
- Versi strategi saat ini
- Agent accuracy rata-rata
- RL training progress

### Definition of Done
- [ ] All health data tersedia
- [ ] Terformat rapi dalam laporan
- [ ] Warning jika ada anomali (uptime rendah, banyak error)
