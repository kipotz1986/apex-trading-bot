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
