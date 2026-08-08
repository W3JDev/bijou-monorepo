# Bijou Core: The Central Nervous System (`src/core/`)

**Status:** Critical / Production
**Language:** Python (FastAPI)

---

## 🏗️ What is this folder?
This is the foundational logic of the Bijou system. It handles:
1.  **Server Lifecycle**: Starting (`bijou.py`), stopping, and reloading.
2.  **Tool Orchestration**: The loop that decides *which* tool to run (`tool_orchestrator.py`).
3.  **API Endpoints**: The dashboard backend (`dashboard_api_simple.py`).
4.  **Database Access**: Global Supabase client wrapper (`supabase_client.py`).

## 🔑 Key Files & Roles

### `bijou.py` -> The Entry Point
*   **Role**: The `main()` application.
*   **Key Function**: `startup_event()` initializes the `BijouAI` singleton.
*   **Agent Note**: If you need to add a new top-level API route (like `/webhook`), do it here.

### `tool_orchestrator.py` -> The "Hands"
*   **Role**: Parses user intent and executes Python functions.
*   **Key Function**: `process_message(content, ...)`
*   **Logic**:
    1.  Receives user text.
    2.  Checks specifically for "trigger phrases" (Calculators, CRM).
    3.  Executes the mapped function.
    4.  Returns the result to the LLM context.

### `dashboard_api_simple.py` -> The Dashboard Backend
*   **Role**: Serves data to the admin panel.
*   **Security**: Uses `verify_session` dependency to enforcing RLS (Row Level Security).
*   **Agent Note**: ALWAYS require `tenant_id` query param or header here.

### `cost_optimizer.py` -> The "Smart Wallet"
*   **Role**: Manages API keys (Gemini/OpenAI) to prevent rate limits.
*   **Logic**: Rotates keys round-robin style.

---

## ⚠️ Developer Warnings
*   **Circular Imports**: `bijou.py` imports `tool_orchestrator.py`. Do NOT import `bijou` in `orchestrator` without type checking guards.
*   **Global State**: `bijou_instance` is a global singleton. Use `app.state.bijou` to access it in routes.
