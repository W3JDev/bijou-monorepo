# Bijou Agents: The Cognitive Centers (`src/agents/`)

**Status:** Evolving / Experimental
**Language:** Python

---

## 🧠 What is this folder?
This folder contains the **Specialized Intelligence** modules. These are not "tools" (hands) but "brains" (perspectives). They modify *how* the AI thinks or speaks.

## 🤖 The Agent Roster

### 1. ASI (Artificial Social Intelligence) - `asi.py`
*   **Role**: The "Vibe Check".
*   **Function**: Analyzes the emotional context of a conversation *before* generating a reply.
*   **Input**: Chat History.
*   **Output**: `sentiment`, `intent`, `suggested_tone`.

### 2. Humanizer - `humanizer.py`
*   **Role**: The "Manglish Engine".
*   **Function**: Rewrites sterile AI text into local Malaysian slang based on the `persona` setting.
*   **Key Logic**:
    *   If `persona="property_agent"`, adds "Boss", "PM tepi".
    *   If `persona="formal"`, keeps it strict.
*   **Agent Note**: This runs *after* the main LLM generation.

### 3. ERS (Escalation & Routing System) - `ers.py`
*   **Role**: The "Supervisor".
*   **Function**: Decides if a human needs to take over.
*   **Triggers**: "Talk to human", "I want refund", "Scam".
*   **Action**: Sets `is_bot_active = False` in the database.

---

## 🔌 Integration
These agents are typically called sequentially in the `BijouAI` main loop in `src/core/bijou.py`.
**Flow**: `User Input` -> `ASI (Analyze)` -> `Orchestrator (Tools)` -> `LLM (Generate)` -> `Humanizer (Rewrite)` -> `Reply`
