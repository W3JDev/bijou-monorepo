import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Mail, MessageCircle } from "lucide-react";
import React, { useState } from "react";

interface FAQItem {
  q: string;
  a: React.ReactNode;
  category: string;
}

const faqs: FAQItem[] = [
  // About Bijou
  {
    category: "About Bijou",
    q: "What exactly is Bijou?",
    a: (
      <>
        Bijou is a Malaysian-built WhatsApp and Telegram AI assistant that
        replies to customers in Manglish, books appointments via Cal.com, and
        escalates complex issues to you via email/WhatsApp. Think of it as a
        24/7 staff member who never sleeps, never forgets, and costs{" "}
        <strong className="text-gold-400">RM299/month</strong> instead of
        RM2,500+/month for a human receptionist.
      </>
    ),
  },
  {
    category: "About Bijou",
    q: "Why did you build Bijou?",
    a: "Founder's story: My mother's life was saved by AI-powered cancer research in 2023. I saw firsthand how AI can change lives — so I built Bijou to help Malaysian SMEs compete with bigger businesses without hiring full-time staff they can't afford.",
  },
  {
    category: "About Bijou",
    q: "Is Bijou a chatbot or a real AI?",
    a: "Real AI powered by GPT-4 — but constrained to ONLY answer from YOUR knowledge base (no hallucination). It doesn't generate random answers. If it doesn't know, it escalates to you.",
  },

  // Malaysian-Specific
  {
    category: "Malaysian Market",
    q: 'Does it understand Manglish? Like "Got or not?", "Can lah", "Tomorrow free ah?"',
    a: (
      <>
        <p className="mb-3">
          YES. Bijou has a custom Manglish engine trained on 20+ Malaysian
          speech patterns. It detects code-switching between BM/English/
          Mandarin/Tamil and replies naturally.
        </p>
        <div className="bg-black/30 rounded-xl p-4 border border-white/10 text-sm font-mono space-y-2">
          <div className="text-gray-400">
            Customer:{" "}
            <span className="text-white">
              "Tmr morning got slot or not? Near LRT can ah?"
            </span>
          </div>
          <div className="text-emerald-400">
            Bijou:{" "}
            <span className="text-white">
              "Got lah! 10am free. Walking distance from LRT station, 5 min
              only."
            </span>
          </div>
        </div>
      </>
    ),
  },
  {
    category: "Malaysian Market",
    q: "Will it work for my industry? (Property agents / F&B / clinics / salons)",
    a: "Yes — we've tested with property agents (most popular), restaurants, medical clinics, and beauty salons. You upload your own FAQs, property listings, menu, or service catalog. The AI learns YOUR business, not generic templates.",
  },
  {
    category: "Malaysian Market",
    q: "My customers speak BM, some speak English, some mix. Will Bijou get confused?",
    a: 'No — it auto-detects language and mirrors the customer. If they speak BM, it replies in BM. If they mix ("Booking untuk esok boleh tak?"), it mixes back naturally.',
  },

  // Pricing
  {
    category: "Pricing & Fees",
    q: "Is RM299/month really all I pay? No conversation fees like other platforms?",
    a: "RM299/month. Period. No per-message fees. No WhatsApp conversation markup (competitors charge 20% on top of Meta fees). No surprise annual lock-in. Cancel anytime.",
  },
  {
    category: "Pricing & Fees",
    q: "What about WhatsApp Business API (WABA) fees? I heard it's expensive.",
    a: (
      <>
        <p className="mb-3">
          Bijou uses the GOWA bridge — you don't need WABA at all. No
          RM280/month Meta subscription. No conversation markups. Zero WABA
          costs.
        </p>
        <p className="mb-2 text-sm text-gray-400 font-semibold">
          Here's what others actually charge:
        </p>
        <div className="space-y-1.5 text-sm">
          <div className="flex justify-between items-center bg-red-500/5 border border-red-500/10 rounded-lg px-3 py-2">
            <span className="text-gray-300">ChatDaddy (advertised ~RM75)</span>
            <span className="text-red-400 font-bold">~RM280–500/mo actual</span>
          </div>
          <div className="flex justify-between items-center bg-red-500/5 border border-red-500/10 rounded-lg px-3 py-2">
            <span className="text-gray-300">Wati</span>
            <span className="text-red-400 font-bold">
              20% markup on Meta fees
            </span>
          </div>
          <div className="flex justify-between items-center bg-red-500/5 border border-red-500/10 rounded-lg px-3 py-2">
            <span className="text-gray-300">DahReply</span>
            <span className="text-red-400 font-bold">~RM700+/mo total</span>
          </div>
          <div className="flex justify-between items-center bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">
            <span className="text-white font-bold">Bijou</span>
            <span className="text-emerald-400 font-bold">
              RM299/mo flat. Always.
            </span>
          </div>
        </div>
      </>
    ),
  },
  {
    category: "Pricing & Fees",
    q: "Do I get locked into an annual contract?",
    a: "NO. Monthly plans cancel anytime. Annual plan (RM2,990 — saves RM598) is optional, and if you cancel early, we refund the unused months. No annual trap.",
  },
  {
    category: "Pricing & Fees",
    q: "What's the refund policy?",
    a: (
      <>
        30-day money-back guarantee. If you set it up, test it, and it doesn't
        work for your business, email{" "}
        <a
          href="mailto:jewel@mybijou.xyz"
          className="text-gold-400 hover:text-gold-300 underline underline-offset-2"
        >
          jewel@mybijou.xyz
        </a>{" "}
        directly — full refund, no questions asked.
      </>
    ),
  },

  // Setup & Technical
  {
    category: "Setup & Technical",
    q: "How long does setup take? I don't have time for 2-week integrations.",
    a: (
      <>
        <p className="mb-3">
          <strong className="text-gold-400">15 minutes.</strong> Here's the full
          process:
        </p>
        <ol className="space-y-1.5 text-sm list-none">
          {[
            "Sign up → verify email (2 min)",
            "Scan WhatsApp QR code (1 min)",
            "Upload your FAQ document or paste FAQs (5 min)",
            "Connect Cal.com calendar — optional (3 min)",
            "Test with a few WhatsApp messages → go live (4 min)",
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-gold-500/20 text-gold-400 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                {i + 1}
              </span>
              <span className="text-gray-300">{step}</span>
            </li>
          ))}
        </ol>
        <p className="mt-3 text-sm text-gray-400">
          No developer needed. No consultants charging RM5,000 for setup.
        </p>
      </>
    ),
  },
  {
    category: "Setup & Technical",
    q: "Do I need to install anything or learn complicated flow builders?",
    a: "No. Bijou runs in the cloud (Singapore servers). You don't install anything. There's no flow builder — the AI handles conversations naturally based on your FAQs, not rigid scripts.",
  },
  {
    category: "Setup & Technical",
    q: "What if I want to change my FAQs or menu later?",
    a: "Log into your dashboard, go to Knowledge Base, and update any FAQ instantly. Changes go live in under 60 seconds — no developer, no support ticket.",
  },
  {
    category: "Setup & Technical",
    q: "What happens when Bijou can't answer a question?",
    a: 'It escalates — sends you a WhatsApp alert and email with the full conversation context, so you can jump in immediately. The customer gets a polite holding message like "Let me connect you with our team" rather than a dead end.',
  },
];

const categories = [...new Set(faqs.map((f) => f.category))];

const categoryActiveClasses: Record<string, string> = {
  All: "bg-white/15 border-white/30 text-white",
  "About Bijou": "bg-yellow-500/15 border-yellow-400/40 text-yellow-300",
  "Malaysian Market":
    "bg-emerald-500/15 border-emerald-400/40 text-emerald-300",
  "Pricing & Fees": "bg-blue-500/15 border-blue-400/40 text-blue-300",
  "Setup & Technical": "bg-purple-500/15 border-purple-400/40 text-purple-300",
};

const categoryInactiveClasses: Record<string, string> = {
  All: "bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-white",
  "About Bijou":
    "bg-white/5 border-white/10 text-gray-400 hover:bg-yellow-500/10 hover:border-yellow-400/20 hover:text-yellow-300",
  "Malaysian Market":
    "bg-white/5 border-white/10 text-gray-400 hover:bg-emerald-500/10 hover:border-emerald-400/20 hover:text-emerald-300",
  "Pricing & Fees":
    "bg-white/5 border-white/10 text-gray-400 hover:bg-blue-500/10 hover:border-blue-400/20 hover:text-blue-300",
  "Setup & Technical":
    "bg-white/5 border-white/10 text-gray-400 hover:bg-purple-500/10 hover:border-purple-400/20 hover:text-purple-300",
};

const categoryDotClasses: Record<string, string> = {
  "About Bijou": "bg-yellow-400",
  "Malaysian Market": "bg-emerald-400",
  "Pricing & Fees": "bg-blue-400",
  "Setup & Technical": "bg-purple-400",
};

export const FAQ: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const filtered =
    activeCategory === "All"
      ? faqs
      : faqs.filter((f) => f.category === activeCategory);

  return (
    <section
      id="faq"
      className="py-24 relative overflow-hidden bg-gradient-to-b from-black/0 via-black/40 to-black/0"
    >
      {/* Background glows */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-0 w-[500px] h-[500px] bg-gold-500/6 rounded-full blur-[150px]" />
        <div className="absolute bottom-1/4 right-0 w-[400px] h-[400px] bg-emerald-500/6 rounded-full blur-[130px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[300px] bg-gold-900/8 rounded-full blur-[120px]" />
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <div className="inline-block px-3 py-1 mb-4 rounded-full bg-gold-500/10 border border-gold-400/20 text-gold-400 text-xs font-bold uppercase tracking-wider">
            Got Questions?
          </div>
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Frequently Asked{" "}
            <span className="text-gradient-gold">Questions</span>
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Real answers from the Bijou team. No sales scripts, no vague
            promises.
          </p>
        </motion.div>

        {/* Category Filter */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="flex flex-wrap gap-2 justify-center mb-10"
        >
          {["All", ...categories].map((cat) => {
            const isActive = activeCategory === cat;
            const activeClass =
              categoryActiveClasses[cat] ?? categoryActiveClasses["All"];
            const inactiveClass =
              categoryInactiveClasses[cat] ?? categoryInactiveClasses["All"];
            return (
              <button
                key={cat}
                onClick={() => {
                  setActiveCategory(cat);
                  setOpenIndex(null);
                }}
                className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all duration-200 ${
                  isActive ? activeClass : inactiveClass
                }`}
              >
                {cat !== "All" && (
                  <span
                    className={`inline-block w-2 h-2 rounded-full mr-2 ${
                      categoryDotClasses[cat] ?? "bg-gray-400"
                    }`}
                  />
                )}
                {cat}
              </button>
            );
          })}
        </motion.div>

        {/* FAQ Grid */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeCategory}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="space-y-3"
          >
            {filtered.map((item, idx) => {
              const isOpen = openIndex === idx;
              const dotClass =
                categoryDotClasses[item.category] ?? "bg-gray-400";
              return (
                <motion.div
                  key={`${activeCategory}-${idx}`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className={`rounded-2xl border transition-all duration-200 ${
                    isOpen
                      ? "border-gold-400/35 bg-gradient-to-br from-gold-500/8 to-transparent shadow-[0_0_40px_rgba(212,175,55,0.08)]"
                      : "border-white/8 bg-white/[0.02] hover:border-white/15 hover:bg-white/[0.04]"
                  }`}
                >
                  <button
                    className="w-full text-left px-6 py-4 flex items-start gap-3"
                    onClick={() => setOpenIndex(isOpen ? null : idx)}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-2 ${dotClass} ${
                        isOpen ? "opacity-100" : "opacity-40"
                      }`}
                    />
                    <span className="flex-1 font-semibold text-white text-sm leading-snug">
                      {item.q}
                    </span>
                    <ChevronDown
                      className={`w-5 h-5 flex-shrink-0 mt-0.5 transition-all duration-300 ${
                        isOpen ? "rotate-180 text-gold-400" : "text-gray-500"
                      }`}
                    />
                  </button>

                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.28, ease: "easeInOut" }}
                        className="overflow-hidden"
                      >
                        <div className="px-6 pb-5 pl-8 text-gray-400 text-sm leading-relaxed border-t border-white/5 pt-3">
                          <span className="text-[9px] font-bold uppercase tracking-widest text-gold-400/50 block mb-2">
                            {item.category}
                          </span>
                          {item.a}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </motion.div>
        </AnimatePresence>

        {/* Bottom CTA — full-width card */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="mt-12"
        >
          <div className="glass-panel-3d rounded-2xl p-8 border border-white/10">
            <div className="flex flex-col md:flex-row md:items-center gap-6">
              <div className="flex-1">
                <p className="text-xl font-bold text-white mb-2">
                  Still have a specific question?
                </p>
                <p className="text-gray-400 text-sm">
                  The founder replies personally — no bots, no support ticket
                  queues.
                </p>
                <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                  Usually responds within 2 hours
                </div>
              </div>
              <div className="flex flex-col sm:flex-row gap-3">
                <a
                  href="https://api.whatsapp.com/send/?phone=60174106981&text=Hi+Jewel!+I+have+a+question+about+Bijou+AI."
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-500/15 border border-emerald-400/30 text-emerald-400 hover:bg-emerald-500/25 rounded-xl text-sm font-semibold transition-all"
                >
                  <MessageCircle className="w-4 h-4" />
                  WhatsApp Founder
                </a>
                <a
                  href="mailto:jewel@mybijou.xyz"
                  className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gold-500/10 border border-gold-400/30 text-gold-400 hover:bg-gold-500/20 rounded-xl text-sm font-semibold transition-all"
                >
                  <Mail className="w-4 h-4" />
                  jewel@mybijou.xyz
                </a>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};
