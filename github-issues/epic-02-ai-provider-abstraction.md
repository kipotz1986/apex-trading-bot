# Epic 2: AI Provider Abstraction Layer

---

## T-2.1: Desain Interface/Abstract Class `AIProvider`

**Labels:** `epic-2`, `ai-core`, `architecture`, `priority-critical`
**Milestone:** Fase 1 — Foundation

### Deskripsi
Membuat abstract class (blueprint) yang mendefinisikan kontrak standar untuk semua AI provider. Dengan cara ini, kode bisnis (agent-agent kita) tidak perlu tahu apakah sedang menggunakan OpenAI, Gemini, atau Claude — mereka hanya memanggil method standar yang sama.

### Analogi Sederhana
Bayangkan remote TV universal. Apapun merek TV-nya (Samsung, LG, Sony), remote-nya sama. Tombol "power" selalu menyalakan TV, tombol "volume" selalu mengatur suara. Abstract class `AIProvider` adalah "remote universal" untuk semua AI.

### Langkah-Langkah Implementasi

#### 1. Buat file `backend/app/core/ai_provider.py`

```python
"""
AI Provider Abstraction Layer.

Semua AI provider (OpenAI, Gemini, Claude, dll) HARUS
mengimplementasikan interface ini. Ini memastikan kita bisa
swap provider tanpa mengubah kode agent apapun.

Usage:
    from app.core.ai_provider import get_ai_provider
    provider = get_ai_provider()
    response = await provider.chat(messages=[...])
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Representasi satu pesan dalam percakapan."""
    role: str  # "system", "user", "assistant"
    content: str


class AIResponse(BaseModel):
    """Respons standar dari AI provider manapun."""
    content: str          # Teks respons utama
    model: str            # Model yang digunakan (e.g., "gpt-4o")
    provider: str         # Provider (e.g., "openai")
    usage: dict = {}      # Token usage {"prompt_tokens": x, "completion_tokens": y}
    raw_response: Any = None  # Raw response asli dari provider (untuk debugging)


class AIProvider(ABC):
    """
    Abstract base class untuk semua AI Provider.
    
    Setiap provider baru (OpenAI, Gemini, Claude, dll) HARUS:
    1. Inherit dari class ini
    2. Implementasi semua method yang ada @abstractmethod
    3. Dibuat di file terpisah (e.g., openai_provider.py)
    """

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> AIResponse:
        """
        Kirim percakapan ke AI dan dapatkan respons.
        
        Args:
            messages: List pesan percakapan (system → user → assistant → ...)
            temperature: Kreativitas (0.0 = deterministik, 1.0 = kreatif)
            max_tokens: Batas maksimal token respons
            json_mode: Jika True, paksa respons dalam format JSON
        
        Returns:
            AIResponse dengan content, usage, dll.
        """
        pass

    @abstractmethod
    async def analyze(
        self,
        system_prompt: str,
        data: str,
        instruction: str,
        json_mode: bool = True,
    ) -> AIResponse:
        """
        Shortcut untuk analisis data. Mengirim system prompt + data + instruksi.
        Digunakan oleh agent-agent untuk analisa pasar.
        
        Args:
            system_prompt: Siapa AI ini (e.g., "Kamu adalah Technical Analyst Expert")
            data: Data mentah yang akan dianalisis (e.g., candlestick data)
            instruction: Apa yang harus dilakukan dengan data tersebut
            json_mode: Jika True, paksa output JSON terstruktur
        
        Returns:
            AIResponse
        """
        pass

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """
        Convert teks menjadi vektor embedding (list angka desimal).
        Digunakan untuk pattern memory (vector database).
        
        Args:
            text: Teks yang akan di-embed
        
        Returns:
            List of float (embedding vector), biasanya 1536 dimensi
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Cek apakah provider ini sedang online dan API key valid.
        Return True jika OK, False jika error.
        """
        pass
```

#### 2. Buat factory function untuk mendapatkan provider

Di file yang sama (`ai_provider.py`), tambahkan di bagian bawah:

```python
from app.core.config import settings


def get_ai_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AIProvider:
    """
    Factory function — dapatkan AI provider sesuai konfigurasi.
    
    Jika tidak ada parameter, gunakan yang di .env.
    
    Usage:
        provider = get_ai_provider()                          # Dari .env
        provider = get_ai_provider("openai", "gpt-4o", "sk-xxx")  # Manual
    
    Raises:
        ValueError: Jika provider_name tidak dikenali
    """
    name = provider_name or settings.AI_PROVIDER
    mdl = model or settings.AI_MODEL
    key = api_key or settings.AI_API_KEY

    if name == "openai":
        from app.core.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=key, model=mdl)
    elif name == "google":
        from app.core.providers.google_provider import GoogleProvider
        return GoogleProvider(api_key=key, model=mdl)
    elif name == "anthropic":
        from app.core.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=key, model=mdl)
    else:
        raise ValueError(
            f"Unknown AI provider: '{name}'. "
            f"Supported: openai, google, anthropic"
        )
```

### Definition of Done
- [ ] File `backend/app/core/ai_provider.py` ada dengan class `AIProvider`, `ChatMessage`, `AIResponse`
- [ ] Abstract methods `chat()`, `analyze()`, `embed()`, `health_check()` terdefinisi
- [ ] Factory function `get_ai_provider()` berfungsi
- [ ] Docstring lengkap di setiap method
- [ ] Bisa di-import tanpa error: `from app.core.ai_provider import AIProvider`

### File yang Dibuat
- `[NEW]` `backend/app/core/ai_provider.py`
- `[NEW]` `backend/app/core/providers/__init__.py`

---

## T-2.2: Implementasi Adapter untuk OpenAI (GPT-4o, GPT-4.1)

**Labels:** `epic-2`, `ai-core`, `integration`, `priority-critical`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-2.1

### Deskripsi
Membuat implementasi konkret dari `AIProvider` untuk OpenAI. Adapter ini menerjemahkan panggilan standar kita (`chat`, `analyze`, `embed`) ke API OpenAI yang sesungguhnya.

### Prerequisites
- `pip install openai` (library resmi OpenAI Python)
- Punya API key OpenAI (dapatkan di https://platform.openai.com/api-keys)

### Langkah-Langkah Implementasi

#### 1. Install dependency
```bash
pip install openai
# Tambahkan ke requirements.txt
echo "openai>=1.30.0" >> backend/requirements.txt
```

#### 2. Buat file `backend/app/core/providers/openai_provider.py`

```python
"""
OpenAI Provider Implementation.

Mengimplementasikan AIProvider interface untuk OpenAI API.
Mendukung model: gpt-4o, gpt-4-turbo, gpt-4.1, gpt-3.5-turbo

Usage:
    provider = OpenAIProvider(api_key="sk-xxx", model="gpt-4o")
    response = await provider.chat(messages=[...])
"""

from openai import AsyncOpenAI
from app.core.ai_provider import AIProvider, AIResponse, ChatMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    """Implementasi AIProvider untuk OpenAI."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key=api_key, model=model)
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("openai_provider_initialized", model=model)

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> AIResponse:
        """Kirim chat completion ke OpenAI API."""
        try:
            # Convert ChatMessage ke format OpenAI
            oai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Setup request kwargs
            kwargs = {
                "model": self.model,
                "messages": oai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Jika json_mode, tambahkan response_format
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            # Panggil API
            response = await self.client.chat.completions.create(**kwargs)

            # Parse response
            choice = response.choices[0]
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            logger.info("openai_chat_completed",
                model=self.model,
                tokens_used=usage["total_tokens"]
            )

            return AIResponse(
                content=choice.message.content or "",
                model=response.model,
                provider="openai",
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            logger.error("openai_chat_error",
                model=self.model,
                error=str(e)
            )
            raise

    async def analyze(
        self,
        system_prompt: str,
        data: str,
        instruction: str,
        json_mode: bool = True,
    ) -> AIResponse:
        """Shortcut untuk analisis — gabungkan system + data + instruction."""
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(
                role="user",
                content=f"## DATA:\n{data}\n\n## INSTRUCTION:\n{instruction}"
            ),
        ]
        return await self.chat(
            messages=messages,
            temperature=0.3,  # Lebih deterministik untuk analisis
            json_mode=json_mode,
        )

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector menggunakan OpenAI."""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("openai_embed_error", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Cek apakah OpenAI API sedang online."""
        try:
            response = await self.client.models.list()
            return True
        except Exception:
            return False
```

#### 3. Buat unit test
```python
# backend/tests/test_openai_provider.py
import pytest
from unittest.mock import AsyncMock, patch
from app.core.providers.openai_provider import OpenAIProvider
from app.core.ai_provider import ChatMessage


@pytest.mark.asyncio
async def test_chat_returns_ai_response():
    """Test bahwa chat() mengembalikan AIResponse yang valid."""
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
    
    # Mock OpenAI API call
    with patch.object(provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock:
        mock.return_value = MockOpenAIResponse(
            content="BUY signal detected",
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
        )
        
        messages = [ChatMessage(role="user", content="Analyze BTC")]
        response = await provider.chat(messages)
        
        assert response.content == "BUY signal detected"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 150
```

### Definition of Done
- [ ] File `backend/app/core/providers/openai_provider.py` ada
- [ ] Class `OpenAIProvider` mengimplementasikan semua method dari `AIProvider`
- [ ] `chat()` berhasil memanggil OpenAI API dan mengembalikan `AIResponse`
- [ ] `analyze()` menerima system prompt + data + instruction
- [ ] `embed()` menghasilkan vector embedding
- [ ] `health_check()` return True/False
- [ ] Unit test lulus
- [ ] Error handling + logging di setiap method

### File yang Dibuat
- `[NEW]` `backend/app/core/providers/openai_provider.py`
- `[NEW]` `backend/tests/test_openai_provider.py`

---

## T-2.3: Implementasi Adapter untuk Google Gemini

**Labels:** `epic-2`, `ai-core`, `integration`, `priority-high`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-2.1

### Deskripsi
Membuat implementasi `AIProvider` untuk Google Gemini. Struktur dan pola kode sama dengan OpenAI adapter (T-2.2), hanya disesuaikan dengan Google Gemini API.

### Prerequisites
- `pip install google-generativeai`
- API key Gemini (dapatkan di https://aistudio.google.com/apikey)

### Langkah-Langkah Implementasi

#### 1. Install dependency
```bash
pip install google-generativeai
echo "google-generativeai>=0.5.0" >> backend/requirements.txt
```

#### 2. Buat file `backend/app/core/providers/google_provider.py`
- Inherit dari `AIProvider`
- Implementasi `chat()` menggunakan `genai.GenerativeModel`
- Implementasi `analyze()` sebagai shortcut
- Implementasi `embed()` menggunakan Gemini embedding model
- Implementasi `health_check()`
- Perhatikan: Format message Gemini berbeda dari OpenAI
  - OpenAI: `{"role": "user", "content": "..."}`
  - Gemini: `{"role": "user", "parts": [{"text": "..."}]}`

#### 3. Pola referensi
Lihat `openai_provider.py` sebagai template — seluruh method harus ada dan return type sama (`AIResponse`).

#### 4. Unit test di `backend/tests/test_google_provider.py`

### Definition of Done
- [ ] File `backend/app/core/providers/google_provider.py` ada
- [ ] Semua method dari `AIProvider` diimplementasikan
- [ ] Format message di-convert dengan benar ke format Gemini
- [ ] Unit test lulus

### File yang Dibuat
- `[NEW]` `backend/app/core/providers/google_provider.py`
- `[NEW]` `backend/tests/test_google_provider.py`

---

## T-2.4: Implementasi Adapter untuk Anthropic Claude

**Labels:** `epic-2`, `ai-core`, `integration`, `priority-high`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-2.1

### Deskripsi
Membuat implementasi `AIProvider` untuk Anthropic Claude. Perhatikan bahwa Claude API memiliki beberapa perbedaan unik dibanding OpenAI:
- System prompt dikirim sebagai parameter terpisah, bukan di dalam messages
- Tidak ada native JSON mode, perlu ditangani lewat prompting

### Prerequisites
- `pip install anthropic`
- API key Claude (dapatkan di https://console.anthropic.com/)

### Langkah-Langkah Implementasi

#### 1. Install dependency
```bash
pip install anthropic
echo "anthropic>=0.25.0" >> backend/requirements.txt
```

#### 2. Buat file `backend/app/core/providers/anthropic_provider.py`
- Inherit dari `AIProvider`
- **PERHATIAN:** Claude mengirim `system` prompt secara terpisah:
  ```python
  response = await client.messages.create(
      model="claude-opus-4-20250514",
      system="You are a trading analyst",    # <-- TERPISAH
      messages=[{"role": "user", "content": "..."}],  # <-- Tanpa system
  )
  ```
- Implementasi semua 4 method
- Untuk `embed()`: Claude tidak punya native embedding. Gunakan fallback ke OpenAI embedding atau return error yang jelas.

#### 3. Unit test di `backend/tests/test_anthropic_provider.py`

### Definition of Done
- [ ] File `backend/app/core/providers/anthropic_provider.py` ada
- [ ] System prompt dikirim dengan benar (sebagai parameter terpisah, bukan di messages)
- [ ] `embed()` ditangani dengan benar (fallback atau error yang jelas)
- [ ] Unit test lulus

### File yang Dibuat
- `[NEW]` `backend/app/core/providers/anthropic_provider.py`
- `[NEW]` `backend/tests/test_anthropic_provider.py`

---

## T-2.5: Implementasi Adapter Fallback (Auto-Switch)

**Labels:** `epic-2`, `ai-core`, `reliability`, `priority-high`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-2.2, T-2.3, T-2.4

### Deskripsi
Membuat wrapper yang otomatis beralih ke fallback provider jika provider utama gagal (error, timeout, rate limited). Ini penting agar bot tidak berhenti total hanya karena satu AI provider sedang down.

### Langkah-Langkah Implementasi

#### 1. Buat file `backend/app/core/providers/fallback_provider.py`

```python
"""
Fallback AI Provider.

Wrapper yang mencoba provider utama dulu, jika gagal
otomatis switch ke provider cadangan.

Usage:
    provider = FallbackProvider(
        primary=OpenAIProvider(...),
        fallback=GoogleProvider(...)
    )
    # Jika OpenAI error, otomatis pakai Gemini
    response = await provider.chat(messages=[...])
"""

from app.core.ai_provider import AIProvider, AIResponse, ChatMessage
from app.core.logging import get_logger
from typing import Optional

logger = get_logger(__name__)


class FallbackProvider(AIProvider):
    """Provider yang memiliki cadangan otomatis."""

    def __init__(self, primary: AIProvider, fallback: Optional[AIProvider] = None):
        self.primary = primary
        self.fallback = fallback
        self._using_fallback = False

    async def chat(self, messages, temperature=0.7, max_tokens=4096, json_mode=False) -> AIResponse:
        try:
            response = await self.primary.chat(messages, temperature, max_tokens, json_mode)
            self._using_fallback = False
            return response
        except Exception as primary_error:
            logger.warning("primary_provider_failed",
                provider=self.primary.__class__.__name__,
                error=str(primary_error)
            )
            if self.fallback:
                logger.info("switching_to_fallback",
                    fallback=self.fallback.__class__.__name__
                )
                self._using_fallback = True
                return await self.fallback.chat(messages, temperature, max_tokens, json_mode)
            raise  # No fallback available, propagate error

    # Implementasikan analyze(), embed(), health_check() dengan pola yang sama
    # (coba primary dulu, fallback jika error)
```

#### 2. Update `get_ai_provider()` di `ai_provider.py`
```python
def get_ai_provider() -> AIProvider:
    primary = _create_provider(settings.AI_PROVIDER, settings.AI_MODEL, settings.AI_API_KEY)
    
    fallback = None
    if settings.AI_FALLBACK_PROVIDER:
        fallback = _create_provider(
            settings.AI_FALLBACK_PROVIDER,
            settings.AI_FALLBACK_MODEL,
            settings.AI_FALLBACK_API_KEY
        )
    
    if fallback:
        return FallbackProvider(primary=primary, fallback=fallback)
    return primary
```

### Definition of Done
- [ ] `FallbackProvider` otomatis switch saat primary gagal
- [ ] Logging jelas: kapan primary gagal, kapan fallback digunakan
- [ ] Jika tidak ada fallback dan primary gagal, error di-propagate dengan jelas
- [ ] Unit test: primary gagal → fallback dipanggil → response berhasil

### File yang Dibuat
- `[NEW]` `backend/app/core/providers/fallback_provider.py`
- `[MODIFY]` `backend/app/core/ai_provider.py`

---

## T-2.6: Unit Test untuk Setiap Adapter + Integration Test Fallback

**Labels:** `epic-2`, `testing`, `priority-high`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-2.2, T-2.3, T-2.4, T-2.5

### Deskripsi
Memastikan semua adapter dan mekanisme fallback bekerja dengan benar melalui automated testing. Test harus bisa jalan **tanpa API key sungguhan** (menggunakan mock).

### Langkah-Langkah
1. Unit test setiap provider: `test_openai_provider.py`, `test_google_provider.py`, `test_anthropic_provider.py`
2. Integration test fallback: `test_fallback_provider.py`
3. Test factory function: `test_get_ai_provider.py`
4. Semua test menggunakan mock (tidak memanggil API sungguhan)

### Test Scenarios
- ✅ Provider berhasil → return `AIResponse` yang valid
- ✅ Provider gagal (exception) → error ter-propagate
- ✅ Fallback: primary gagal → fallback berhasil → return response
- ✅ Fallback: primary gagal + fallback gagal → error ter-propagate
- ✅ Factory: provider name valid → return provider yang benar
- ✅ Factory: provider name invalid → raise ValueError

### Definition of Done
- [ ] Semua test file ada di `backend/tests/`
- [ ] `pytest backend/tests/` → semua PASS
- [ ] Coverage minimal 80% untuk seluruh provider code

---

## T-2.7: Konfigurasi Pemilihan Provider via `.env`

**Labels:** `epic-2`, `configuration`, `priority-medium`
**Milestone:** Fase 1 — Foundation
**Depends On:** T-2.5

### Deskripsi
Memastikan alur end-to-end dari `.env` → `config.py` → `get_ai_provider()` → provider yang benar bekerja sempurna. Dokumentasikan cara mengganti provider di README.

### Langkah-Langkah
1. Pastikan `.env.example` memiliki semua variabel AI yang dibutuhkan (sudah di T-1.4)
2. Test: ubah `AI_PROVIDER=google` di `.env` → restart → `get_ai_provider()` return `GoogleProvider`
3. Test: ubah `AI_PROVIDER=anthropic` → `get_ai_provider()` return `AnthropicProvider`
4. Tambah section di README: "How to Switch AI Provider"

### Definition of Done
- [ ] Mengganti `AI_PROVIDER` di `.env` cukup untuk switch provider
- [ ] README memiliki dokumentasi cara switch provider
- [ ] Tidak perlu ubah kode apapun untuk ganti provider
