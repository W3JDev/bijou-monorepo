import { motion } from "framer-motion";
import { ArrowRight, MessageCircle, Zap } from "lucide-react";
import React, { useState } from "react";
import { useTranslation } from "react-i18next";

interface WaitlistStripProps {
  className?: string;
  onOpenModal: () => void;
}

export const WaitlistStrip: React.FC<WaitlistStripProps> = ({
  className = "",
  onOpenModal,
}) => {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleChat = async () => {
    const waUrl = `https://api.whatsapp.com/send/?phone=60174106981&text=${encodeURIComponent("Hi! I want to learn more about Bijou AI")}`;
    if (email.trim() && !submitted) {
      setSubmitting(true);
      try {
        await fetch("/api/leads", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.trim(),
            source: "waitlist",
            name: "",
          }),
        });
        setSubmitted(true);
      } catch {}
      setSubmitting(false);
    }
    window.open(waUrl, "_blank", "noopener,noreferrer");
  };

  const pills = [
    { icon: "✅", text: t("waitlist.pill1") },
    { icon: "⚡", text: t("waitlist.pill2") },
    { icon: "🚫", text: t("waitlist.pill3") },
  ];

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-40 ${className}`}
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      {/* Glow blur above strip */}
      <div className="h-4 bg-gradient-to-t from-emerald-900/30 to-transparent pointer-events-none" />

      <div className="bg-gradient-to-r from-[#0a1f12] via-[#0d2b19] to-[#0a1f12] backdrop-blur-xl border-t border-emerald-400/20 shadow-[0_-12px_50px_rgba(16,185,129,0.18)] relative overflow-hidden">
        {/* Shimmer line at top */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-400/50 to-transparent" />
        {/* Subtle animated glow */}
        <motion.div
          animate={{ opacity: [0.4, 0.7, 0.4] }}
          transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
          className="absolute inset-0 bg-gradient-to-r from-emerald-900/10 via-emerald-600/5 to-emerald-900/10 pointer-events-none"
        />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 relative z-10">
          <div className="flex items-center justify-between gap-4">
            {/* Left: headline + pills */}
            <div className="flex-1 min-w-0">
              {/* Headline */}
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <motion.span
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{
                    repeat: Infinity,
                    duration: 2,
                    ease: "easeInOut",
                  }}
                  className="text-lg"
                >
                  🔥
                </motion.span>
                <span className="text-white font-black text-sm sm:text-base leading-tight">
                  {t("waitlist.headline")}
                </span>
              </div>

              {/* Pills — desktop */}
              <div className="hidden sm:flex items-center gap-2 flex-wrap">
                {pills.map((p, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] font-semibold"
                  >
                    {p.icon} {p.text}
                  </span>
                ))}
                <span className="text-gray-500 text-[10px]">
                  {/* Fix 3: Source "500+ Malaysian SMEs" — replaced with honest place-based proof */}
                  · {t("waitlist.social")}
                </span>
              </div>

              {/* Mobile subtext */}
              <p className="sm:hidden text-emerald-300/70 text-[10px] font-medium">
                {t("waitlist.mobileSub")}
              </p>
            </div>

            {/* CTA area: email input + chat button + claim button */}
            <div className="flex-shrink-0 flex items-center gap-2">
              {/* Email input — sm+ only */}
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleChat()}
                placeholder="your@email.com"
                className="hidden sm:block w-40 lg:w-48 bg-black/50 border border-emerald-500/30 rounded-xl px-3 py-2.5 text-white text-xs placeholder-gray-500 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition-all"
              />

              {/* Chat icon button with pulsing flash animation */}
              <div className="relative flex-shrink-0">
                {/* Outer pulse ring */}
                <motion.div
                  animate={{ scale: [1, 1.6, 1], opacity: [0.5, 0, 0.5] }}
                  transition={{
                    repeat: Infinity,
                    duration: 2,
                    ease: "easeOut",
                  }}
                  className="absolute inset-0 rounded-xl bg-emerald-400/30 pointer-events-none"
                />
                <motion.button
                  onClick={handleChat}
                  disabled={submitting}
                  whileHover={{
                    scale: 1.07,
                    boxShadow: "0 0 28px rgba(16,185,129,0.55)",
                  }}
                  whileTap={{ scale: 0.94 }}
                  className="relative flex items-center gap-1.5 px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl font-bold text-xs sm:text-sm whitespace-nowrap bg-black/60 border border-emerald-500/40 text-emerald-400 shadow-[0_0_14px_rgba(16,185,129,0.25)] transition-all disabled:opacity-60"
                >
                  <motion.div
                    animate={{ rotate: [0, -8, 8, 0] }}
                    transition={{
                      repeat: Infinity,
                      duration: 3,
                      ease: "easeInOut",
                      repeatDelay: 1,
                    }}
                  >
                    <MessageCircle className="w-4 h-4" />
                  </motion.div>
                  <span className="hidden sm:inline">
                    {submitted ? "✓ Noted!" : submitting ? "..." : "Chat"}
                  </span>
                </motion.button>
              </div>

              {/* Claim My Spot button */}
              <motion.button
                onClick={onOpenModal}
                whileHover={{
                  scale: 1.04,
                  boxShadow: "0 0 30px rgba(16,185,129,0.5)",
                }}
                whileTap={{ scale: 0.97 }}
                className="flex items-center gap-2 px-4 sm:px-6 py-2.5 sm:py-3 rounded-xl font-black text-sm sm:text-base whitespace-nowrap bg-gradient-to-r from-emerald-500 to-green-400 text-black shadow-[0_0_20px_rgba(16,185,129,0.35)] transition-all"
              >
                <Zap className="w-4 h-4" />
                <span>{t("waitlist.cta")}</span>
                <ArrowRight className="w-4 h-4 hidden sm:block" />
              </motion.button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
