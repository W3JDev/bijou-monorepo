-- #3 (2026-09-21): Soft per-contact "stop the AI texting this person" toggle.
--
-- The owner can pause AI auto-replies for ONE contact while still receiving and
-- reading that contact's messages in the dashboard (to reply manually). This is
-- deliberately different from the two existing mechanisms:
--   * blocked_numbers  -> HARD drop: the message is ignored entirely.
--   * escalations      -> human takeover: implies an agent is actively handling.
-- ai_paused is a lightweight per-contact mute the owner flips on/off at will.
--
-- Additive and non-destructive. Defaults to FALSE so every existing contact keeps
-- getting AI replies exactly as before. Read by bijou.py::_is_ai_paused (fail-open)
-- and written by the dashboard toggle POST /api/dashboard/contact/ai-pause.
ALTER TABLE public.contacts
  ADD COLUMN IF NOT EXISTS ai_paused boolean NOT NULL DEFAULT false;
