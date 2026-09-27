import { motion } from "framer-motion";
import { Phone, Mic, Send } from "lucide-react";
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

// Telnyx AI Assistant "Bijou Sales Concierge" (packages/voice/scripts/setup-telnyx-assistant.mjs).
// The id is public by design: the widget needs only this, and the assistant has
// supports_unauthenticated_web_calls enabled. No credential reaches the browser.
const VOICE_AGENT_ID = "assistant-a50eb00d-262b-450f-be62-aca2839069fa";
const WIDGET_SRC = "https://unpkg.com/@telnyx/ai-agent-widget@0.36.0/dist/bundle.min.js";
const SALES_LINE_TEL = "+13079999692";
const SALES_LINE_DISPLAY = "+1 (307) 999-9692";

// Load the ~550KB widget only once the section is on screen, and only once.
let widgetPromise: Promise<void> | null = null;
function loadWidget(): Promise<void> {
  if (!widgetPromise) {
    widgetPromise = new Promise((resolve, reject) => {
      const el = document.createElement("script");
      el.src = WIDGET_SRC;
      el.async = true;
      el.onload = () => resolve();
      el.onerror = () => {
        widgetPromise = null;
        reject(new Error("voice widget failed to load"));
      };
      document.head.appendChild(el);
    });
  }
  return widgetPromise;
}

const callScript = [
  { speaker: "Customer", text: "Hi, is anyone available to help me?" },
  {
    speaker: "Bijou",
    text: "Absolutely! This is Bijou. How can I help you today?",
  },
  { speaker: "Customer", text: "I'd like to book an appointment for tomorrow morning." },
  {
    speaker: "Bijou",
    text: "Of course — would 10am or 11am suit you? Let me check availability now.",
  },
  { speaker: "Customer", text: "10am please." },
  {
    speaker: "Bijou",
    text: "Done! 10am is confirmed. I'll send you a reminder tonight. Anything else I can help with?",
  },
];

export const VoiceComingSoon: React.FC = () => {
  const { t } = useTranslation();
  const [inView, setInView] = useState(false);
  const [widget, setWidget] = useState<"idle" | "ready" | "failed">("idle");
  useEffect(() => {
    if (!inView) return;
    loadWidget().then(
      () => setWidget("ready"),
      () => setWidget("failed"),
    );
  }, [inView]);
  const [email, setEmail] = useState("");
  // Three explicit states: idle, submitted (server said ok), failed
  // (server said no OR network error). Fixes audit finding #37 — the
  // previous version caught every error and showed success, so a
  // user whose endpoint was down thought they were on the waitlist
  // and never got the launch email.
  const [submitted, setSubmitted] = useState(false);
  const [failed, setFailed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || submitted) return;
    setSubmitting(true);
    setFailed(false);
    try {
      const response = await fetch("/api/voice-waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), source: "voice-teaser" }),
      });
      if (response.ok) {
        setSubmitted(true);
      } else {
        setFailed(true);
      }
    } catch {
      // Network error or fetch threw — show a retry path, not a lie.
      setFailed(true);
    }
    setSubmitting(false);
  };

  return (
    <section className="py-24 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gold-600/8 rounded-full blur-[160px]" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 rounded-full bg-gold-500/10 border border-gold-500/20 text-gold-400 text-xs font-bold uppercase tracking-wider">
            <Mic className="w-3 h-3" />
            {t("voice.live.badge")}
          </div>
          <h2 className="text-3xl md:text-5xl font-black text-white mb-4">
            Bijou speaks.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-gold-300 to-gold-500">
              In your brand voice.
            </span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Voice calls — same Bijou brain, same warmth. Answers your
            phone when you can't. Books, qualifies, escalates.{" "}
            <strong className="text-white">No call center needed.</strong>
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-12 items-start max-w-5xl mx-auto">
          {/* Left: Phone call mockup */}
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            {/* Phone UI */}
            <div className="glass-panel-3d rounded-3xl border border-gold-500/20 overflow-hidden max-w-sm mx-auto">
              {/* Call header */}
              <div className="bg-gold-600/30 px-4 py-4 flex items-center justify-between border-b border-gold-500/20">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gold-300 to-gold-500 flex items-center justify-center">
                    <Phone className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <div className="text-white text-sm font-bold">
                      {t("voice.live.callerLabel")}
                    </div>
                    <div className="text-gold-300 text-xs">
                      {SALES_LINE_DISPLAY}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-gold-400 text-xs">
                  <span className="w-1.5 h-1.5 bg-gold-400 rounded-full animate-pulse" />
                  Live
                </div>
              </div>

              {/* Call transcript */}
              <div className="bg-black/40 px-4 py-4 space-y-3 min-h-[280px]">
                {callScript.map((line, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.15 }}
                    onViewportEnter={() => setActiveIdx(i)}
                    className={`flex gap-2 ${line.speaker === "Bijou" ? "flex-row-reverse" : ""}`}
                  >
                    <div
                      className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-black ${
                        line.speaker === "Bijou"
                          ? "bg-gradient-to-br from-gold-300 to-gold-500 text-white"
                          : "bg-white/10 text-gray-400"
                      }`}
                    >
                      {line.speaker === "Bijou" ? "B" : "C"}
                    </div>
                    <div
                      className={`max-w-[75%] rounded-xl px-3 py-2 text-xs ${
                        line.speaker === "Bijou"
                          ? "bg-gold-600/40 border border-gold-500/20 text-gold-300"
                          : "bg-white/8 text-gray-300"
                      } ${activeIdx === i ? "opacity-100" : "opacity-60"}`}
                    >
                      {line.text}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Call footer */}
              <div className="bg-gold-600/20 px-4 py-2 text-center border-t border-gold-500/10">
                <p className="text-gold-400 text-xs font-semibold">
                  Call handled. Appointment booked. Owner notified.
                </p>
              </div>
            </div>
          </motion.div>

          {/* Right: Waitlist form */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="space-y-6"
            onViewportEnter={() => setInView(true)}
          >
            {/* Primary: live voice call with the Bijou Sales Concierge */}
            <div className="glass-panel-3d rounded-2xl border border-gold-500/40 p-6 space-y-4 shadow-[0_0_30px_rgba(227,180,87,0.15)]">
              <h3 className="text-2xl font-black text-white flex items-center gap-2">
                <Mic className="w-5 h-5 text-gold-400" />
                {t("voice.live.title")}
              </h3>
              <p className="text-gray-400 text-sm">{t("voice.live.body")}</p>
              <div className="min-h-[56px]" data-testid="voice-widget-slot">
                {widget === "ready" &&
                  React.createElement("telnyx-ai-agent", {
                    "agent-id": VOICE_AGENT_ID,
                    position: "static",
                  })}
                {widget === "idle" && (
                  <p className="text-gray-500 text-sm">{t("voice.live.loading")}</p>
                )}
              </div>
              {widget !== "failed" && (
                <p className="text-gray-600 text-xs">{t("voice.live.mic")}</p>
              )}
              <div className="flex flex-wrap items-center gap-2 text-sm text-gray-300">
                <span>{t("voice.live.orCall")}</span>
                <a
                  href={`tel:${SALES_LINE_TEL}`}
                  className="inline-flex items-center gap-1.5 font-bold text-gold-300 hover:text-gold-200 underline-offset-4 hover:underline"
                >
                  <Phone className="w-4 h-4" />
                  {SALES_LINE_DISPLAY}
                </a>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-bold text-white">
                {t("voice.waitlist.title")}
              </h3>
              <p className="text-gray-400">
                Voice AI for US & EU businesses — WhatsApp already works. Your phone
                is next. Join the waitlist and we'll reach out when it ships in
                Q4 2026.
              </p>

              {/* Features list */}
              <ul className="space-y-2.5">
                {[
                  "Answers calls in English + multilingual",
                  "Books, reschedules, cancels appointments",
                  "Qualifies leads: budget + intent detection",
                  "Escalates to human when needed",
                  "Works with your existing phone number",
                ].map((feat, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-2.5 text-sm text-gray-300"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-gold-400 flex-shrink-0" />
                    {feat}
                  </li>
                ))}
              </ul>
            </div>

            {/* Email form */}
            <div className="glass-panel-3d rounded-2xl border border-gold-500/20 p-6">
              {submitted ? (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-4"
                >
                  <div className="text-3xl mb-3">✅</div>
                  <h4 className="text-white font-bold text-lg mb-1">
                    You&apos;re on the list!
                  </h4>
                  <p className="text-gray-400 text-sm">
                    We&apos;ll email you when Bijou Voice goes live. You&apos;ll be first.
                  </p>
                </motion.div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-white text-sm font-semibold mb-2">
                      Email address
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@yourbusiness.com"
                      required
                      className="w-full bg-black/40 border border-gold-500/30 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-gold-500/60 focus:ring-1 focus:ring-gold-500/30 transition-all"
                    />
                  </div>
                  {failed && (
                    <div
                      role="alert"
                      className="rounded-lg p-3 text-sm bg-red-500/10 border border-red-500/30 text-red-300"
                    >
                      Couldn&apos;t reach the waitlist endpoint. Please try again, or
                      WhatsApp us directly at{" "}
                      <a
                        href="https://wa.me/60174106981"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline"
                      >
                        +60 17-410 6981
                      </a>
                      .
                    </div>
                  )}
                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-gold-500 to-gold-600 text-white hover:from-gold-400 hover:to-gold-500 transition-all shadow-[0_0_20px_rgba(227,180,87,0.35)] disabled:opacity-60"
                  >
                    <Send className="w-4 h-4" />
                    {submitting ? "Joining..." : failed ? "Try again" : "Join Voice Waitlist"}
                  </button>
                  <p className="text-gray-600 text-xs text-center">
                    No spam. One email when it ships. Unsubscribe anytime.
                  </p>
                </form>
              )}
            </div>

            {/* ETA callout */}
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gold-500/5 border border-gold-500/10">
              <div className="w-8 h-8 rounded-full bg-gold-500/10 flex items-center justify-center flex-shrink-0">
                <Mic className="w-4 h-4 text-gold-400" />
              </div>
              <div>
                <div className="text-white text-xs font-bold">
                  Target: Q4 2026
                </div>
                <div className="text-gray-500 text-xs">
                  WhatsApp + Telegram already live at $499/mo — Voice is next.
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
