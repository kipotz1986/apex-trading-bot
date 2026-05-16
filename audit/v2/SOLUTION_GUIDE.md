# Audit v2 Solution Guide

This document describes how to fix the current issues and harden the system.

## 1. Fix the live price extraction bug

Files:
- `backend/app/services/bot_runner.py`
- `backend/app/agents/orchestrator.py`

Recommended change:
- In `bot_runner.py`, keep `market_data["candles"]` as multi-timeframe candle data.
- In `orchestrator.py`, compute `current_price` from a known timeframe path, for example `1h` or the highest-resolution candle list.

Example fix:
```python
candles = market_data.get("candles", {})
price_candles = candles.get("1h") or next(iter(candles.values()), [])
current_price = price_candles[-1].close if price_candles else 0.0
```

Validation:
- Ensure `current_price` is derived from a list of normalized candle objects.
- Add a guard to avoid execution if `current_price <= 0`.

## 2. Make settings real and consistent

Files:
- `backend/app/api/settings.py`
- `frontend/src/app/(authenticated)/settings/page.tsx`
- `frontend/src/hooks/useSettings.ts`

Recommended changes:
1. Implement persistence for settings in the database or environment store.
2. Replace hardcoded risk values with actual persisted values.
3. If full persistence is not yet ready, clearly label the page as `Read-only / Simulation Mode`.
4. Add PUT handlers or frontend API calls to save `ai` and `risk` settings.
5. Ensure `Switch` has `onCheckedChange` and `Button` actions are wired to real save/discard logic.

Example frontend fix for the toggle:
```tsx
<Switch
  checked={settings?.advancedReasoningEnabled}
  onCheckedChange={(value) => setSettings(prev => prev ? {...prev, advancedReasoningEnabled: value} : prev)}
/>
```

## 3. Improve metrics transparency

Files:
- `backend/app/api/agents.py`

Recommended changes:
- Replace `patterns_learned = total_trades * 3` with an explicit derived metric or remove it.
- Do not expose static fallback `model_version` values as if they are meaningful version metadata.
- Add schema / documentation comments to clarify which metrics are real production metrics and which are heuristics.

## 4. Align copy trading comments with behavior

Files:
- `backend/app/services/copy_trading/leaderboard.py`

Recommended changes:
- Remove stale comments that mention `mock data` if the implementation uses actual API access.
- If the service should support offline fallback data, implement a real fallback mechanism rather than returning an empty list silently.
- Log a clear warning when leaderboard fetch returns empty due to external service failure.

## 5. Validation and testing

Suggested tests:
- Add a unit test for `orchestrator.decide()` verifying `current_price` extraction works when `market_data["candles"]` is a dict.
- Add a test for `/api/settings` to assert the API returns the expected fields and not placeholder hardcoded values when persistence is enabled.
- Add a React test or smoke test for `SettingsPage` to verify the `Switch` renders and is interactive when handlers are attached.

## 6. Priority order

1. Fix `current_price` data shape mismatch in `orchestrator.py`.
2. Wire actual settings persistence or make the UI explicitly read-only.
3. Clarify backend metrics and copy trading comments.
4. Add tests covering these paths.

## 7. Notes for junior developers

- The frontend `settings` page is currently more of a dashboard than a configuration editor.
- The backend API returns some values as simulation, so do not assume saving settings will affect live trading until persistence is implemented.
- The highest-risk bug is the incorrect assumption about candle data structure when extracting the current asset price.
