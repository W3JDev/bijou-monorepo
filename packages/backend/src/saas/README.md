# Bijou SaaS: The Business Logic (`src/saas/`)

**Status:** Stable
**Language:** Python

---

## 🏢 What is this folder?
This folder turns the "Chatbot" into a "Business". It handles **Multi-Tenancy**, **Billing**, and **Onboarding**.
Without this folder, Bijou is just a single bot. With it, it's a Platform.

## 📦 Key Concepts

### Multi-Tenancy (`tenant_manager.py`)
*   **Concept**: Every request must belong to a `tenant_id`.
*   **Logic**:
    *   Loads `ClientConfig` from Supabase (`tenants` table).
    *   Injects tenant-specific System Prompts (e.g., "You are a Dentist" vs "You are a Realtor").
    *   **Agent Note**: Never assume a default prompt. Always load dynamic config.

### Onboarding (`onboarding_api.py`)
*   **Concept**: The flow from "Stranger" to "Paid User".
*   **Flow**:
    1.  User pays on Stripe.
    2.  Webhook triggers `create_tenant`.
    3.  System provisions a new `tenant_id`.
    4.  System calls Bridge to allocate a WhatsApp slot.

### Plans & Limits (`plan_manager.py`)
*   **Concept**: Free Tier vs Pro Tier.
*   **Logic**:
    *   Checks `message_count` vs `plan_limit`.
    *   If exceeded, `ToolOrchestrator` stops processing and sends "Upgrade" message.

---

## 🛡️ Security Rule
**Data Isolation**: All SQL queries in this module MUST include `.eq('tenant_id', current_tenant_id)`.
**NO EXEC EXCEPTIONS**.
