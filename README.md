# APEX Trading Bot

Advanced, self-learning Multi-Agent AI Trading Bot.

## Overview
APEX is a sophisticated trading system powered by multiple AI agents that collaborate to analyze market data, manage risk, and execute trades in real-time.

## Configuration

APEX use environment variables for configuration. Copy the template and fill in your credentials:

```bash
cp .env.example .env
```

### Key Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_PROVIDER` | Selection of AI engine (openai, google, anthropic) | `openai` |
| `AI_MODEL` | Specific model to use (e.g., `gpt-4o`) | `gpt-4o` |
| `EXCHANGE_NAME` | The trading exchange to connect to (bybit, binance) | `bybit` |
| `EXCHANGE_TESTNET` | Set to `true` for paper trading, `false` for live trading | `true` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://...` |

For more details, see the documentation in `.env.example`.

## How to Switch AI Provider

APEX is designed with a provider-agnostic abstraction layer. You can switch between different AI engines simply by updating your `.env` file:

### 1. OpenAI (Default)
```ini
AI_PROVIDER=openai
AI_MODEL=gpt-4o
AI_API_KEY=sk-xxxx
```

### 2. Google Gemini
```ini
AI_PROVIDER=google
AI_MODEL=gemini-1.5-pro
AI_API_KEY=YOUR_GEMINI_KEY
```

### 3. Anthropic Claude
```ini
AI_PROVIDER=anthropic
AI_MODEL=claude-3-5-sonnet-20240620
AI_API_KEY=YOUR_CLAUDE_KEY
```

### Fallback Mechanism
For high reliability, you can configure a secondary provider that will be used automatically if the primary provider fails:
```ini
AI_FALLBACK_PROVIDER=google
AI_FALLBACK_MODEL=gemini-1.5-pro
AI_FALLBACK_API_KEY=YOUR_GEMINI_KEY
```

## Development Setup

1. **Infrastructure**: Start the required services using Docker:
   ```bash
   docker-compose up -d
   ```

2. **Backend**: Install dependencies and start the FastAPI server:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. **Frontend**: Set up the Next.js dashboard:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## License
MIT
