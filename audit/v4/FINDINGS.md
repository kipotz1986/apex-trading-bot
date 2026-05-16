# Audit v4 Detailed Findings

## 1. Backend: Orchestrator and DB session forwarding

### 1.1 `backend/app/core/factory.py`
- The active DB session is now passed into `MasterOrchestrator` via `db=db`.
- This removes the previous v3 issue where the orchestrator held `self.db = None` and risk settings fell back to hardcoded defaults.

### 1.2 `backend/app/agents/orchestrator.py`
- `MasterOrchestrator.decide()` now forwards `db=self.db` to `RiskManagerAgent.analyze()`.
- This means saved values from `SystemSettings` can be applied during live trade risk analysis.

## 2. Backend: On-chain stats fallback bug

### 2.1 `backend/app/services/bot_runner.py`
- The fallback branch for non-BTC symbols uses `asyncio.sleep(0)`.
- Since `asyncio.sleep(0)` completes successfully with `None`, the safe-gather wrapper returns `None` instead of the intended default `{}`.
- Result: `market_data["onchain_stats"]` becomes `None` for non-BTC symbols, which is acceptable in the current upstream code but is not the intended fallback behavior.

## 3. Frontend: Settings UX

### 3.1 `frontend/src/app/(authenticated)/settings/page.tsx`
- The settings page is now correctly interactive and can save/discard changes.
- The `Update Credentials` button remains a UI-only element without a connected backend endpoint.
- This is a usability gap rather than a runtime failure.

## 4. Settings API behavior

### 4.1 `backend/app/api/settings.py`
- The GET endpoint reads persisted values from `SystemSettings`.
- PUT endpoints for AI and risk settings now persist values and audit the updates.
- This is a strong improvement and matches the intended settings workflow.

## 5. Miscellaneous observations

- `backend/app/api/agents.py` now uses `PatternMemory.count()` for `patterns_learned`, which is better than the earlier synthetic multiplier.
- No new compilation issues were found in the audited files.
- The copy trading leaderboard implementation remains real API-driven and no longer suggests mock data use.
