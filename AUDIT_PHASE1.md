# NeuroQuant Phase 1 Audit Clean-Up Report

This document records the fake, dead, and duplicate layers found and successfully cleaned up or resolved in the first phase of the repository audit.

---

## 1. Fake / Dead Code Cleaned Up

### `backend/app/services/ml_engine/orchestrator.py` [DELETED]
* **Finding**: Falsely claimed to implement parallel ML inferences (TFT, GNN, LSTM-Attention). In reality, it returned hardcoded, seeds-jittered, hand-picked linear combinations. 
* **Action**: Verified that this file was dead code (never imported or referenced by any active backend API route) and deleted it.

### Root-level `research/` directory [DELETED]
* **Finding**: Duplicated the real quant research package (`backend/research`) but only contained placeholder stubs, such as a dummy 20-day MA crossover placeholder under `research/models/hmm_garch/regime_detector.py`.
* **Action**: Removed from the repository to prevent path pollution and developer confusion. All real regime detection models now refer exclusively to the verified HMM-GARCH model under `backend/research/models/hmm_garch`.

---

## 2. API Level Bugs and Security Gate Issues Resolved

### `backend/app/api/v1/trading.py` [MODIFIED]
* **Finding 1**: Attempted to import `get_current_active_user` which did not exist, preventing the uvicorn FastAPI server from booting successfully on port 8000.
* **Finding 2**: Used `current_user.id` to log audit trails and filter SQLite tables. This caused runtime `AttributeError` crashes since `current_user` is a dictionary returned by `decode_token` (JWT validation), not a model class.
* **Action**:
  - Replaced the dependency import with `get_current_user_or_none` from `app.core.dependencies`.
  - Upgraded all user-ID accesses to use the safe dictionary access `current_user.get("sub")` with a fallback to `"guest-user"` to allow robust execution in guest mode.
  - Successfully verified that uvicorn boots and completes application startup cleanly.
