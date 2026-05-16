# Audit v4 Solution Guide

This guide covers the remaining remediation and validation steps for the current codebase.

## 1. Fix the on-chain stats fallback path

Files:
- `backend/app/services/bot_runner.py`

Issue:
- Non-BTC symbols use `asyncio.sleep(0)` as a placeholder task.
- Since this task resolves to `None`, the fallback default `{}` is never used.

Recommended fix:
- Replace `asyncio.sleep(0)` with `asyncio.sleep(0, {})` or use a small helper coroutine that explicitly returns an empty dictionary.

Example fix:
```python
onchain_stats_task = safe_gather(
    onchain.get_btc_onchain_stats() if coin == "BTC" else asyncio.sleep(0, {}),
    "onchain_stats",
    {}
)
```

Validation:
- Confirm `market_data["onchain_stats"]` is `{}` for non-BTC symbols.
- Add a unit test or logging assertion for the fallback branch.

## 2. Clarify or implement credential update UX

Files:
- `frontend/src/app/(authenticated)/settings/page.tsx`
- optional backend credential update endpoint

Recommendations:
- If credential management is out of scope, change the button label to `Coming Soon` or remove it.
- If credentials are supported, implement a secure backend endpoint and wire the button to that API.

## 3. Keep DB-backed risk persistence verified

Files:
- `backend/app/core/factory.py`
- `backend/app/agents/orchestrator.py`
- `backend/app/agents/risk_manager.py`

Recommendations:
- Verify that `RiskManagerAgent.analyze()` uses `SystemSettings.get_value()` with a real `db` session.
- Consider adding a small integration test that changes `SystemSettings` and confirms the new values affect risk validation.

## 4. Validation checklist

1. Run syntax validation:
   - `python3 -m py_compile backend/app/core/factory.py backend/app/agents/orchestrator.py backend/app/services/bot_runner.py backend/app/api/settings.py backend/app/api/agents.py backend/app/agents/fundamental.py`
2. Test API settings persistence:
   - GET `/api/settings`
   - PUT `/api/settings/risk`
   - GET `/api/settings` and verify updated values persist.
3. Test fallback branch for onchain stats:
   - Simulate a non-BTC symbol and verify `market_data["onchain_stats"]` is `{}`.
4. Review frontend settings UX:
   - Confirm save/discard work.
   - Decide whether `Update Credentials` should remain inactive or be implemented.
