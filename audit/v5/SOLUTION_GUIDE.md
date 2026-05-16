# Audit v5 Solution Guide

This guide describes how to remove the remaining simulation gaps uncovered in audit v5.

## 1. Replace mock copy trading position tracking

Files:
- `backend/app/services/copy_trading/position_tracker.py`

Recommended changes:
- Implement real position fetch from exchange or a copy trading API.
- Remove hardcoded `entry_price` and `size_usd` values.
- Persist actual trader positions and only create events from real changes.

Validation:
- Confirm `_fetch_trader_positions_from_exchange()` returns real data.
- Add a test covering the event creation logic for OPEN/CLOSE transitions.

## 2. Improve portfolio reporting

Files:
- `backend/app/api/portfolio.py`

Recommended changes:
- Calculate `daily_pnl` from recent trades or equity deltas.
- Use live position data for `unrealized_pnl` when available.
- Separate `balance` and `equity` explicitly if they differ.

Validation:
- Verify the portfolio summary endpoint returns non-zero PnL when there are open positions.
- Add tests for the fallback behavior when `RiskState` is missing.

## 3. Integrate the backtest route with the actual orchestrator

Files:
- `backend/app/api/backtest.py`
- `backend/app/services/backtesting.py`

Recommended changes:
- Provide a proper orchestrator instance to `BacktestEngine`.
- If a lightweight mock is needed, clearly separate the simulated backtest path from production backtesting.
- Remove placeholder comments once the route uses real workflow code.

Validation:
- Run a backtest request and confirm the returned results come from real strategy decisions.
- Add an integration test for `/api/backtest/run`.

## 4. Use real feature vectors in RL environment

Files:
- `backend/app/services/learning/trading_environment.py`

Recommended changes:
- Replace random observation generation with a call to `StateSpace` or a real feature pipeline.
- Ensure observations are deterministic and derived from `historical_data`.

Validation:
- Confirm `env.reset()` and `env.step()` return consistent observations for the same input data.
- Add unit tests for `_get_observation()`.

## 5. Remove placeholder metrics from the self-learning dashboard

Files:
- `backend/app/api/agents.py`

Recommended changes:
- Replace hardcoded `accuracy: 0.88` with a real metric or omit it until available.
- Use actual model metadata for `model_version` or label fallback state clearly.
- Document which dashboard values are experimental.

Validation:
- Verify `/api/agents/learning` returns real values when training data exists.
- Add tests for the fallback response format.

## 6. Validation checklist

1. Ensure no `mock` or `placeholder` comments remain in production-critical backend flows.
2. Run the existing audit backend compile check again.
3. Create regression tests for:
   - copy trading position event generation,
   - portfolio summary PnL calculation,
   - backtest workflow integration,
   - RL environment observation pipeline,
   - learning metrics fallback behavior.
