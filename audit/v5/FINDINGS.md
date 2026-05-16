# Audit v5 Detailed Findings

## 1. Copy Trading: Position Tracker is mocked

### File: `backend/app/services/copy_trading/position_tracker.py`
- The tracker explicitly documents that current positions are fetched from exchange using mocked logic.
- `_fetch_trader_positions_from_exchange()` returns hardcoded positions for trader IDs `T001` and `T004` only.
- `_create_event()` uses `entry_price=60000.0` and `size_usd=1000.0` as mock values.

Impact:
- Copy trading signals can be generated from synthetic events, not real exchange activity.
- This makes the copy trading agent unreliable for live deployment.

## 2. Portfolio summary uses placeholder values

### File: `backend/app/api/portfolio.py`
- `daily_pnl` is hardcoded to `0.0`.
- `unrealized_pnl` is hardcoded to `0.0`.
- `balance` is simplified to `risk_state.current_equity`.

Impact:
- Portfolio and PnL dashboards are not reflecting live performance accurately.
- Users may be presented with incomplete financial reporting.

## 3. Backtest route remains simplified / placeholder

### File: `backend/app/api/backtest.py`
- The backtest route notes the orchestrator initialization is complex and may need a factory.
- It instantiates `BacktestEngine(db, None)` with a `None` orchestrator.
- This implies the backtest path is not fully integrated with the real decision engine.

Impact:
- Backtesting is not a reliable reproduction of live strategy behavior.
- It cannot be used for robust strategy validation until the orchestrator is integrated.

## 4. RL training environment is not realistic

### File: `backend/app/services/learning/trading_environment.py`
- `_get_observation()` returns `np.random.uniform(-1, 1, (25,))` instead of actual market state.
- The environment is explicitly labeled as mocked for training speed.

Impact:
- RL training is happening on randomized state representations rather than real feature vectors.
- Learned policies may not generalize to actual market conditions.

## 5. Dashboard learning metrics are placeholders

### File: `backend/app/api/agents.py`
- When there is no recent order analysis, the learning endpoint returns `accuracy: 0.88` as a hardcoded placeholder.
- `model_version` falls back to a bootstrapped static string rather than real model metadata.

Impact:
- Self-learning dashboard can mislead users with synthetic confidence metrics.
- This should be clearly labeled or replaced with real analytics.
