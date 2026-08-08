import { AnimatePresence, motion } from "framer-motion";
import {
    ArrowRight,
    BookOpen,
    CheckCircle2,
    ExternalLink,
    Loader2,
    Mail,
    Presentation,
    Rocket,
    X,
} from "lucide-react";
import React, { useState } from "react";

interface SlideDeckModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SlideDeckModal: React.FC<SlideDeckModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [step, setStep] = useState<"form" | "loading" | "success" | "error">(
    "form",
  );
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStep("loading");
    setErrorMsg("");

    try {
      const response = await fetch("/api/slide-deck", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.toLowerCase().trim(),
          name: name.trim(),
        }),
      });

      const result = await response.json();
      if (!response.ok)
        throw new Error(result.message || "Something went wrong");

      setStep("success");
    } catch (err: any) {
      setErrorMsg(err.message || "Aiyo, server hiccup. Try again boss.");
      setStep("error");
    }
  };

  const resetAndClose = () => {
    onClose();
    setTimeout(() => {
      setStep("form");
      setEmail("");
      setName("");
      setErrorMsg("");
    }, 300);
  };

  const resources = [
    {
      icon: <Presentation className="w-5 h-5" />,
      label: "Sales Presentation",
      desc: "Full Bijou AI slide deck with pricing & case studies",
      url: "https://app.mybijou.xyz/static/sales-presentation.html",
      color: "from-blue-600 to-blue-500",
    },
    {
      icon: <BookOpen className="w-5 h-5" />,
      label: "User Guide",
      desc: "Step-by-step onboarding & setup walkthrough",
      url: "https://app.mybijou.xyz/static/user-guide.html",
      color: "from-emerald-700 to-emerald-500",
    },
    {
      icon: <Rocket className="w-5 h-5" />,
      label: "Start Free Trial",
      desc: "30-day money-back · No credit card · 5-min setup",
      url: "https://app.mybijou.xyz/signup",
      color: "from-amber-700 to-yellow-500",
    },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={resetAndClose}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[110]"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", stiffness: 300, damping: 28 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-[111] p-4"
          >
            <div className="glass-panel-3d bg-dark-900/95 border border-white/10 rounded-3xl overflow-hidden shadow-[0_0_60px_rgba(0,0,0,0.6)] relative">
              {/* Close */}
              <button
                onClick={resetAndClose}
                className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-full transition-colors z-10"
              >
                <X className="w-5 h-5" />
              </button>

              {/* Glow */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-32 bg-blue-500/15 blur-[50px] pointer-events-none" />

              <div className="p-8 relative z-10">
                {/* ── FORM ── */}
                {step === "form" && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-bold uppercase tracking-wider mb-5">
                      <Presentation className="w-3.5 h-3.5" />
                      Instant Access
                    </div>

                    <h3 className="text-2xl font-display font-bold text-white mb-2">
                      Get the Full Bijou AI Deck
                    </h3>
                    <p className="text-gray-400 text-sm mb-6 leading-relaxed">
                      Enter your email and we'll send you the slide deck, user
                      guide, and onboarding link — all in one email, instantly.
                    </p>

                    {/* Preview of what they get */}
                    <div className="space-y-2 mb-6">
                      {resources.map((r) => (
                        <div
                          key={r.label}
                          className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/5 border border-white/8"
                        >
                          <div
                            className={`w-8 h-8 rounded-lg bg-gradient-to-br ${r.color} flex items-center justify-center text-white flex-shrink-0`}
                          >
                            {r.icon}
                          </div>
                          <div>
                            <p className="text-white text-sm font-semibold leading-none mb-0.5">
                              {r.label}
                            </p>
                            <p className="text-gray-500 text-xs">{r.desc}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-3">
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full bg-black/50 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all text-sm"
                        placeholder="Your name (optional)"
                      />
                      <input
                        required
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-black/50 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all text-sm"
                        placeholder="your@email.com"
                      />
                      <button
                        type="submit"
                        className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-bold py-3.5 rounded-xl transition-all transform hover:scale-[1.01] flex items-center justify-center gap-2"
                      >
                        <Mail className="w-4 h-4" />
                        Send Me the Resources
                        <ArrowRight className="w-4 h-4" />
                      </button>
                      <p className="text-center text-xs text-gray-600">
                        No spam. Just the resources.
                      </p>
                    </form>
                  </motion.div>
                )}

                {/* ── LOADING ── */}
                {step === "loading" && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="py-16 flex flex-col items-center justify-center text-center"
                  >
                    <Loader2 className="w-10 h-10 text-blue-400 animate-spin mb-4" />
                    <h3 className="text-lg font-bold text-white mb-1">
                      Sending your resources...
                    </h3>
                    <p className="text-gray-500 text-sm">Almost there!</p>
                  </motion.div>
                )}

                {/* ── SUCCESS ── */}
                {step === "success" && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="py-8 flex flex-col items-center text-center"
                  >
                    <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mb-5 relative">
                      <div className="absolute inset-0 bg-emerald-500/20 rounded-full animate-ping" />
                      <CheckCircle2 className="w-8 h-8 text-emerald-400 relative z-10" />
                    </div>
                    <h3 className="text-2xl font-display font-bold text-white mb-2">
                      Check your inbox! 📬
                    </h3>
                    <p className="text-gray-400 text-sm mb-6 max-w-xs leading-relaxed">
                      We've sent the slide deck, user guide, and onboarding link
                      to{" "}
                      <span className="text-emerald-400 font-semibold">
                        {email}
                      </span>
                    </p>

                    {/* Quick access links */}
                    <div className="w-full space-y-2 mb-6">
                      {resources.map((r) => (
                        <a
                          key={r.label}
                          href={r.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-white/5 border border-white/8 hover:bg-white/10 transition-colors w-full"
                        >
                          <div className="flex items-center gap-3">
                            <div
                              className={`w-7 h-7 rounded-lg bg-gradient-to-br ${r.color} flex items-center justify-center text-white flex-shrink-0`}
                            >
                              {React.cloneElement(
                                r.icon as React.ReactElement<{ className?: string }>,
                                { className: "w-4 h-4" },
                              )}
                            </div>
                            <span className="text-white text-sm font-medium">
                              {r.label}
                            </span>
                          </div>
                          <ExternalLink className="w-3.5 h-3.5 text-gray-500" />
                        </a>
                      ))}
                    </div>

                    <div className="flex gap-3 w-full">
                      <a
                        href="mailto:"
                        className="flex-1 flex items-center justify-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20 font-semibold py-3 rounded-xl transition-all text-sm"
                      >
                        <Mail className="w-4 h-4" />
                        Open Email App
                      </a>
                      <button
                        onClick={resetAndClose}
                        className="flex-1 bg-white/5 hover:bg-white/10 text-gray-300 font-semibold py-3 rounded-xl transition-all text-sm"
                      >
                        Close
                      </button>
                    </div>
                  </motion.div>
                )}

                {/* ── ERROR ── */}
                {step === "error" && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="py-12 flex flex-col items-center text-center"
                  >
                    <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mb-5">
                      <span className="text-3xl">😅</span>
                    </div>
                    <h3 className="text-xl font-bold text-white mb-3">
                      Aiyo, hiccup lah!
                    </h3>
                    <p className="text-gray-400 text-sm mb-6">{errorMsg}</p>
                    <div className="flex gap-3">
                      <button
                        onClick={() => setStep("form")}
                        className="bg-white/10 hover:bg-white/20 text-white font-bold py-3 px-6 rounded-xl transition-all text-sm"
                      >
                        Try Again
                      </button>
                      <button
                        onClick={resetAndClose}
                        className="bg-white/5 hover:bg-white/10 text-gray-400 font-semibold py-3 px-6 rounded-xl transition-all text-sm"
                      >
                        Close
                      </button>
                    </div>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
