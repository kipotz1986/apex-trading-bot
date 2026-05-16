# Audit v3 Detailed Findings

## 1. Backend: Orchestrator / Settings Persistence

### 1.1 `backend/app/core/factory.py`
- `ServiceFactory.get_orchestrator()` calls `MasterOrchestrator(...)` but does not pass the `db` argument.
- `MasterOrchestrator.__init__()` accepts `db: Session = None` and stores it as `self.db`.
- Since `db` is never provided, `self.db` remains `None` inside the orchestrator.

### 1.2 `backend/app/agents/orchestrator.py`
- `MasterOrchestrator.decide()` correctly passes `db=self.db` to `self.risk_manager.analyze()`.
- However, because `self.db` is `None`, the risk manager uses fallback hardcoded risk values instead of the DB-backed settings.
- This means `/api/settings` persistence is ineffective for live risk decisions.

## 2. Backend: Risk manager fallback logic

### 2.1 `backend/app/agents/risk_manager.py`
- `analyze()` retrieves dynamic limits from `SystemSettings` only when `db` is provided.
- A hardcoded fallback remains in place for `max_exposure = 20.0` and a secondary fallback for `max_pos_pct = 5.0` when `db` is missing.
- This is acceptable as a safety fallback, but the current orchestration path still enters fallback mode due to the factory issue.

## 3. Backend: Settings API correctness

### 3.1 `backend/app/api/settings.py`
- The GET route now reads `daily_loss_limit`, `max_leverage`, `max_position_size`, and `advanced_reasoning_enabled` from DB via `SystemSettings`.
- The PUT handlers now persist changes to DB and audit the updates.
- This is a valid improvement and likely the most important fix from v2.

## 4. Frontend: Settings page

### 4.1 `frontend/src/app/(authenticated)/settings/page.tsx`
- The page now stores `localSettings`, supports `onCheckedChange`, and implements `handleSave` and `handleDiscard`.
- This fixes the earlier read-only UI problem.
- `Update Credentials` is still a button with no handler, so the exchange credentials section remains UI-only.

## 5. Metrics and copy trading

### 5.1 `backend/app/api/agents.py`
- `patterns_learned` is now derived from `PatternMemory.count()`, which is better than the previous synthetic `total_trades * 3` formula.
- The `model_version` fallback still defaults to `v4.2.1-init` if no checkpoint exists; this is a semantic fallback rather than a direct bug.

### 5.2 `backend/app/services/copy_trading/leaderboard.py`
- The service now makes a real https call to the Bybit leaderboard endpoint.
- If the request fails or the response is empty, it returns an empty list rather than mock data.
- This change is correct, but it means the copy trader agent may often return `NEUTRAL` in degraded environments.

## 6. Summary of findings

- The previous core v2 issues are mostly addressed.
- The remaining functional issue is the DB session not being forwarded into `MasterOrchestrator` from `ServiceFactory`.
- Minor uplift items:
  - credential UI remains unimplemented,
  - `max_exposure` in risk manager is still hardcoded,
  - model version fallback is still static when no model exists.
