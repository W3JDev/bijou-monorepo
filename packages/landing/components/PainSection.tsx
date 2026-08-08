import { motion } from "framer-motion";
import { Quote, X } from "lucide-react";
import React from "react";

const competitorPains = [
  {
    brand: "ChatDaddy",
    color: "#25D366",
    quote:
      "The software is complicated and not user-friendly at all. Once you paid, you're left to figure things out on your own.",
    suffix: "— Real G2 review",
  },
  {
    brand: "DahReply",
    color: "#7B5EA7",
    quote:
      "The bot led us to even further work instead of freeing us from it. Support takes days to respond.",
    suffix: "— Real Capterra review",
  },
  {
    brand: "Wati / WABA",
    color: "#128C7E",
    quote:
      "They still charged a full year subscription fee. The bot won't let me talk to a real person. And there's a 20% markup on every conversation.",
    suffix: "— Independent analysis",
  },
];

const bijouFlips = [
  {
    emoji: "🗣️",
    title: "Sounds Malaysian, not robotic",
    chatDaddy: '"Certainly! I can assist you with scheduling a viewing."',
    bijou:
      '"Sure thing! Morning or evening better for you? Can do Saturday lah."',
  },
  {
    emoji: "💸",
    title: "No WABA. No markups. No surprises.",
    chatDaddy: "Hidden WABA fees + 20% conversation markup + annual lock-in",
    bijou: "Flat RM299/month. Zero conversation fees. Cancel anytime.",
  },
  {
    emoji: "⚡",
    title: "Live in 15 minutes, not 15 days",
    chatDaddy: "Flow builders → Developers → Consultants → RM5,000 setup",
    bijou: "Scan QR → Upload FAQs → Go live. No dev needed.",
  },
];

export const PainSection: React.FC = () => {
  return (
    <section className="py-20 relative overflow-hidden bg-gradient-to-b from-black to-dark-900">
      {/* Subtle red tint — represents pain */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-48 bg-red-900/10 rounded-full blur-[100px]" />
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <p className="text-red-400/70 text-xs font-bold uppercase tracking-widest mb-3">
            Sound familiar?
          </p>
          <h2 className="text-3xl md:text-4xl font-display font-extrabold text-white mb-3">
            You&apos;ve tried a chatbot before.
            <br />
            <span className="text-red-400">Here&apos;s why it failed.</span>
          </h2>
          <p className="text-gray-500 text-sm max-w-lg mx-auto">
            These are real reviews from real Malaysian businesses who tried
            other tools first.
          </p>
        </motion.div>

        {/* Competitor pain quotes */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
          {competitorPains.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="relative bg-red-950/20 border border-red-500/15 rounded-2xl p-5"
            >
              {/* Brand label */}
              <div className="flex items-center gap-2 mb-3">
                <div
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-gray-500 text-xs font-bold uppercase tracking-wider">
                  {item.brand}
                </span>
              </div>

              <Quote className="w-5 h-5 text-red-400/40 mb-2" />

              <p className="text-gray-300 text-sm leading-relaxed mb-3 italic">
                &ldquo;{item.quote}&rdquo;
              </p>

              <p className="text-gray-600 text-xs">{item.suffix}</p>

              {/* X mark */}
              <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-red-500/15 flex items-center justify-center">
                <X className="w-3 h-3 text-red-400" />
              </div>
            </motion.div>
          ))}
        </div>

        {/* Divider flip */}
        <motion.div
          initial={{ opacity: 0, scaleX: 0 }}
          whileInView={{ opacity: 1, scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="relative flex items-center gap-4 mb-10"
        >
          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent" />
          <div className="flex-shrink-0 px-4 py-1.5 rounded-full border border-emerald-500/30 bg-emerald-900/20 text-emerald-400 text-xs font-bold uppercase tracking-wider">
            Here&apos;s what Bijou does differently
          </div>
          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent" />
        </motion.div>

        {/* Bijou flips — 3 columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {bijouFlips.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="bg-emerald-950/20 border border-emerald-500/20 rounded-2xl p-5"
            >
              <div className="text-2xl mb-3">{item.emoji}</div>
              <h3 className="text-white text-sm font-bold mb-4">
                {item.title}
              </h3>

              {/* Before */}
              <div className="flex items-start gap-2 mb-2">
                <X className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-gray-500 text-xs leading-relaxed">
                  {item.chatDaddy}
                </p>
              </div>

              {/* After */}
              <div className="flex items-start gap-2">
                <div className="w-3.5 h-3.5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                </div>
                <p className="text-emerald-300 text-xs font-semibold leading-relaxed">
                  {item.bijou}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
