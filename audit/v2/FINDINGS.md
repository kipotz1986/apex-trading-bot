# Audit v2 Detailed Findings

## 1. Backend: Live trading pipeline

### 1.1 `backend/app/services/bot_runner.py`
- `MarketDataService.get_multi_timeframe_candles()` returns a dictionary keyed by timeframe.
- `bot_runner.py` stores this result into `market_data["candles"]`.
- This is correct for multi-TF technical analysis, but the value is not a list.

### 1.2 `backend/app/agents/orchestrator.py`
- The price extraction uses:
  - `current_price = market_data.get("candles", [])[-1].get("close")`
- Because `market_data["candles"]` is a dict, this line is semantically incorrect and may raise an exception or produce invalid behavior at runtime.
- Impact: trade execution can fail with `TypeError` / `KeyError`, forcing the orchestrator to fallback to HOLD or crash during the execution stage.

### 1.3 Risk and execution path
- The orchestrator does a correct final risk validation and execution flow, but it depends on a `current_price` derived from the wrong data shape.
- This is the single highest-risk issue in the current code.

## 2. Backend: Settings and API behavior

### 2.1 `backend/app/api/settings.py`
- The `/api/settings` GET route returns hardcoded values for `dailyLossLimit`, `maxLeverage`, `maxPositionSize`, and `advancedReasoningEnabled`.
- `update_ai_settings` and `update_risk_settings` only write audit logs, they do not persist any updated configuration.
- This means the frontend settings page can display values but cannot actually change live behavior.

### 2.2 `backend/app/api/agents.py`
- `/api/agents/learning` constructs `patterns_learned` as `total_trades * 3`.
- This is a synthetic metric and may be misleading if users expect actual learned pattern counts.
- `model_version` fallback is statically set to `v4.2.1-init` when no model file exists.

## 3. Backend: Copy trading service

### 3.1 `backend/app/services/copy_trading/leaderboard.py`
- Comment text claims the environment will use mock data for development.
- Actual implementation calls the Bybit leaderboard endpoint and returns an empty list on failure.
- Risk: stale comments can mislead developers to think a mock fallback is in use, while the real behavior is a silent empty fallback.

### 3.2 `backend/app/agents/copy_trader.py`
- CopyTradingAgent correctly returns NEUTRAL if no active traders are available.
- The logic is reasonable, but the dependency on external leaderboard availability means this agent may often be neutral in offline or blocked environments.

## 4. Frontend: Settings page

### 4.1 `frontend/src/app/(authenticated)/settings/page.tsx`
- The page fetches settings successfully from `/api/settings`.
- `Switch checked={settings?.advancedReasoningEnabled}` is a controlled component with no `onCheckedChange` or event handler.
- This will render a non-interactive toggle and may trigger a React warning.
- The `Save System Configuration` and `Discard Changes` buttons are present, but there is no handler wired to persist changes or reset values.

### 4.2 Data presentation
- The page exposes placeholder UI for API key and secret masks, which is acceptable for security, but it does not provide a path to manage keys.
- The risk settings values come from hardcoded API response values rather than dynamically persisted configuration.

## 5. General observations

- Python syntax check for audited files passed.
- No broken page route was found for the settings page and the backend route exists.
- There is a mix of production-style behavior and simulation/placeholder behavior across the codebase.
- The system is not yet fully production-ready because settings are not persisted and live trading price extraction has a fatal data shape mismatch.
