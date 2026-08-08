import { motion } from "framer-motion";
import { Phone, Mic, Send } from "lucide-react";
import React, { useState } from "react";

const callScript = [
  { speaker: "Customer", text: "Hello? Boleh tolong saya tak?" },
  {
    speaker: "Bijou",
    text: "Boleh boss! Bijou kat sini. Apa yang you perlukan hari ni?",
  },
  { speaker: "Customer", text: "I want to book appointment, tomorrow morning." },
  {
    speaker: "Bijou",
    text: "Sure boss — 10am or 11am? I check availability now ah.",
  },
  { speaker: "Customer", text: "10am please." },
  {
    speaker: "Bijou",
    text: "Done! 10am confirmed. I send WhatsApp reminder tonight. Anything else I can help?",
  },
];

export const VoiceComingSoon: React.FC = () => {
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
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-900/8 rounded-full blur-[160px]" />
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
          <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-bold uppercase tracking-wider">
            <Mic className="w-3 h-3" />
            Coming Q4 2026
          </div>
          <h2 className="text-3xl md:text-5xl font-black text-white mb-4">
            Bijou speaks.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
              In Manglish.
            </span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Voice calls — same Bijou brain, same Manglish warmth. Answers your
            phone when you can't. Books, qualifies, escalates.{" "}
            <strong className="text-white">No call center needed.</strong>
          </p>
          {/* MS */}
          <p className="text-gray-600 text-sm mt-3 max-w-xl mx-auto">
            Bijou akan jawab telefon anda dalam Manglish — buat appointment,
            qualify lead, dan escalate bila perlu. Tanpa call center.
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
            <div className="glass-panel-3d rounded-3xl border border-purple-500/20 overflow-hidden max-w-sm mx-auto">
              {/* Call header */}
              <div className="bg-purple-900/30 px-4 py-4 flex items-center justify-between border-b border-purple-500/20">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center">
                    <Phone className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <div className="text-white text-sm font-bold">
                      Incoming Call
                    </div>
                    <div className="text-purple-300 text-xs">
                      +60 12-XXX XXXX
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-purple-400 text-xs">
                  <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse" />
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
                          ? "bg-gradient-to-br from-purple-400 to-pink-500 text-white"
                          : "bg-white/10 text-gray-400"
                      }`}
                    >
                      {line.speaker === "Bijou" ? "B" : "C"}
                    </div>
                    <div
                      className={`max-w-[75%] rounded-xl px-3 py-2 text-xs ${
                        line.speaker === "Bijou"
                          ? "bg-purple-900/40 border border-purple-500/20 text-purple-100"
                          : "bg-white/8 text-gray-300"
                      } ${activeIdx === i ? "opacity-100" : "opacity-60"}`}
                    >
                      {line.text}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Call footer */}
              <div className="bg-purple-900/20 px-4 py-2 text-center border-t border-purple-500/10">
                <p className="text-purple-400 text-xs font-semibold">
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
          >
            <div className="space-y-4">
              <h3 className="text-2xl font-black text-white">
                Get early access.
              </h3>
              <p className="text-gray-400">
                Voice AI for Malaysian SMEs — WhatsApp already works. Your phone
                is next. Join the waitlist and we'll reach out when it ships in
                Q4 2026.
              </p>

              {/* Features list */}
              <ul className="space-y-2.5">
                {[
                  "Answers calls in Manglish, English, BM",
                  "Books, reschedules, cancels appointments",
                  "Qualifies leads: budget + intent detection",
                  "Escalates to human when needed",
                  "Works with your existing phone number",
                ].map((feat, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-2.5 text-sm text-gray-300"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0" />
                    {feat}
                  </li>
                ))}
              </ul>
            </div>

            {/* Email form */}
            <div className="glass-panel-3d rounded-2xl border border-purple-500/20 p-6">
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
                      placeholder="boss@yourbusiness.com.my"
                      required
                      className="w-full bg-black/40 border border-purple-500/30 rounded-xl px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-purple-500/60 focus:ring-1 focus:ring-purple-500/30 transition-all"
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
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-400 hover:to-pink-400 transition-all shadow-[0_0_20px_rgba(168,85,247,0.3)] disabled:opacity-60"
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
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-purple-500/5 border border-purple-500/10">
              <div className="w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center flex-shrink-0">
                <Mic className="w-4 h-4 text-purple-400" />
              </div>
              <div>
                <div className="text-white text-xs font-bold">
                  Target: Q4 2026
                </div>
                <div className="text-gray-500 text-xs">
                  WhatsApp + Telegram already live at RM299/mo — Voice is next.
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
