# Audit v3 Solution Guide

This guide explains how to close the remaining gap and harden the system.

## 1. Fix DB session forwarding into the orchestrator

Files:
- `backend/app/core/factory.py`
- `backend/app/agents/orchestrator.py`

Issue:
- `ServiceFactory.get_orchestrator()` creates `MasterOrchestrator` without passing the active `db` session.
- As a result, `MasterOrchestrator` uses `self.db = None` and `RiskManagerAgent.analyze()` falls back to static defaults.

Recommended fix:
- Add `db=db` to the `MasterOrchestrator(...)` call in `ServiceFactory.get_orchestrator()`.

Example:
```python
        return MasterOrchestrator(
            ai_provider=factory.ai,
            technical_agent=factory.technical,
            fundamental_agent=factory.fundamental,
            sentiment_agent=factory.sentiment,
            risk_manager=factory.risk_manager,
            copy_trader=copy_trader,
            consensus_engine=factory.consensus,
            regime_detector=factory.regime_detector,
            regime_strategy=factory.regime_strategy,
            agent_scorer=agent_scorer,
            execution_engine=execution,
            pre_trade_validator=validator,
            state_space=factory.state_space,
            pattern_memory=factory.pattern_memory,
            db=db
        )
```

Validation:
- After this fix, the orchestrator should use DB-backed values for daily loss, max leverage, and max position size during risk analysis.
- Add a test or temporary log in `RiskManagerAgent.analyze()` to confirm `db is not None` inside orchestrator execution.

## 2. Harden risk manager configuration

Files:
- `backend/app/agents/risk_manager.py`
- `backend/app/models/system_settings.py`

Recommendations:
- Add `max_exposure` and other risk levers to `SystemSettings` so they can be tuned without code changes.
- Consider removing hardcoded fallback values or clearly labeling them as emergency defaults.
- Ensure `SystemSettings` stores booleans, floats, and integers consistently.

## 3. Improve frontend credential UX

Files:
- `frontend/src/app/(authenticated)/settings/page.tsx`
- Optional backend endpoint(s) for secure exchange credential updates.

Recommendations:
- Either remove the inactive `Update Credentials` button or wire it to a real API endpoint.
- If credential storage is not implemented, label the section as `Not configurable from UI yet`.

## 4. Clarify fallback metadata and logs

Files:
- `backend/app/api/agents.py`
- `backend/app/services/copy_trading/leaderboard.py`

Recommendations:
- Document that `model_version = v4.2.1-init` is a bootstrapped fallback.
- Log a distinct warning when the copy-trading leaderboard returns no traders to avoid silent NEUTRAL behavior.

## 5. Validation steps

1. Run full backend compilation:
   - `python3 -m py_compile backend/app/agents/orchestrator.py backend/app/api/settings.py backend/app/api/agents.py backend/app/services/bot_runner.py backend/app/models/system_settings.py backend/app/core/factory.py`
2. Test settings flow:
   - GET `/api/settings`
   - PUT `/api/settings/risk` and `/api/settings/ai`
   - Confirm new values are read back by GET `/api/settings`
3. Test orchestrator risk behavior:
   - Verify `RiskManagerAgent.analyze()` receives a real DB session from `MasterOrchestrator`.
4. Validate frontend:
   - Use the Settings page to toggle `Advanced Reasoning`, modify risk fields, and save/discard.

## 6. Priority order

1. Fix `db=db` forwarding in `backend/app/core/factory.py`.
2. Confirm `RiskManagerAgent` uses DB settings when orchestrator is running.
3. Clarify or implement credential editing UX.
4. Preserve or improve fallback logging for metrics and copy trading.
