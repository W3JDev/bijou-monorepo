import { AnimatePresence, motion } from "framer-motion";
import {
    Bell,
    BookOpen,
    Brain,
    CalendarCheck,
    ChevronDown,
    EyeOff,
    FileKey,
    Languages,
    MessageCircle,
    Send,
    Server,
    Shield,
    ShieldCheck,
    UserCheck,
} from "lucide-react";
import React, { useState } from "react";
import { useTranslation } from "react-i18next";

// --- Interactive Widgets ---
const ManglishDialWidget = () => {
  const [level, setLevel] = useState(50);
  const responses = [
    "Good morning. How may I assist you today?",
    "Hi boss, can I help you find something?",
    "Walao boss! What you need? I settle for you fast fast lah!",
  ];
  const tier = level < 33 ? 0 : level < 66 ? 1 : 2;
  return (
    <div className="w-full flex flex-col gap-3 px-1">
      <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider text-gray-500">
        <span>Corporate</span>
        <span>Full Manglish</span>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        value={level}
        onChange={(e) => setLevel(parseInt(e.target.value))}
        className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
      />
      <div className="bg-[#1a2530] p-3 rounded-lg border border-white/5 relative">
        <div className="absolute -top-2 left-4 w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-b-[5px] border-b-[#1a2530]" />
        <AnimatePresence mode="wait">
          <motion.p
            key={tier}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
            className="text-sm text-emerald-100 italic"
          >
            &quot;{responses[tier]}&quot;
          </motion.p>
        </AnimatePresence>
      </div>
    </div>
  );
};

const TraceWidget = () => {
  // Fix 2 (2026-05-15 code-read): Only HandoverSystem (ERS-equiv) runs in production.
  // ASI/Humanizer/SRP are files only — not imported in bijou.py.
  const steps = [
    {
      label: "Gemini 2.5 Flash",
      bg: "bg-purple-500/10 border-purple-500/20",
      dot: "bg-purple-400",
      color: "text-purple-400",
    },
    {
      label: "Handover System",
      bg: "bg-emerald-500/10 border-emerald-500/20",
      dot: "bg-emerald-400",
      color: "text-emerald-400",
    },
  ];
  return (
    <div className="flex items-center gap-1.5 w-full flex-wrap">
      {steps.map((s, i) => (
        <React.Fragment key={i}>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.15 }}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-bold ${s.bg} ${s.color}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
            {s.label}
          </motion.div>
          {i < steps.length - 1 && (
            <span className="text-gray-600 text-xs">&#8594;</span>
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

const CalWidget = () => (
  <div className="space-y-2 w-full">
    {[
      {
        time: "Tomorrow 10am",
        status: "Confirmed",
        color: "text-emerald-400",
        icon: "✅",
      },
      {
        time: "Fri 2pm",
        status: "Available",
        color: "text-blue-400",
        icon: "📅",
      },
      { time: "Sat 11am", status: "Taken", color: "text-red-400", icon: "❌" },
    ].map((slot, i) => (
      <motion.div
        key={i}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: i * 0.1 }}
        className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2 border border-white/5"
      >
        <span className="text-gray-300 text-xs">{slot.time}</span>
        <span className={`text-xs font-semibold ${slot.color}`}>
          {slot.icon} {slot.status}
        </span>
      </motion.div>
    ))}
  </div>
);

const SecurityWidget = () => (
  <div className="grid grid-cols-2 gap-2 w-full">
    {[
      {
        icon: <Server className="w-4 h-4" />,
        label: "Row-Level Security",
        color: "text-blue-400",
      },
      {
        icon: <ShieldCheck className="w-4 h-4" />,
        label: "PDPA Ready",
        color: "text-emerald-400",
      },
      {
        icon: <EyeOff className="w-4 h-4" />,
        label: "Data Isolation",
        color: "text-purple-400",
      },
      {
        icon: <FileKey className="w-4 h-4" />,
        label: "AES-256",
        color: "text-orange-400",
      },
    ].map((item, i) => (
      <div
        key={i}
        className="bg-white/5 rounded-xl flex flex-col items-center justify-center p-2.5 border border-white/5 gap-1"
      >
        <span className={item.color}>{item.icon}</span>
        <span className="text-[10px] text-gray-400 text-center leading-tight">
          {item.label}
        </span>
      </div>
    ))}
  </div>
);

const EscalationWidget = () => {
  const [triggered, setTriggered] = useState(false);
  return (
    <div className="w-full space-y-2">
      <div className="bg-[#1a2530] rounded-lg p-2.5 border border-white/5 space-y-1.5">
        <div className="flex gap-2 items-start">
          <span className="text-[10px] text-gray-500 shrink-0">Customer:</span>
          <span className="text-xs text-gray-300 italic">
            &quot;This is the third time I am asking. No one is helping!&quot;
          </span>
        </div>
        <div className="flex gap-2 items-start">
          <span className="text-[10px] text-emerald-400 font-bold shrink-0">
            Bijou:
          </span>
          <span className="text-xs text-gray-300 italic">
            &quot;I am escalating you to our team right now boss.&quot;
          </span>
        </div>
      </div>
      <button
        onClick={() => setTriggered(true)}
        className="w-full text-xs py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 font-bold transition-all hover:bg-amber-500/20"
      >
        {triggered ? "📧 Owner Notified via Email ✓" : "Simulate Escalation →"}
      </button>
    </div>
  );
};

// --- Feature Definitions ---
const features = [
  {
    icon: <MessageCircle className="w-5 h-5" />,
    color: "emerald",
    badge: "Live Now",
    title: "WhatsApp AI Agent",
    subtitle: "No WABA. No Meta fees. No markups.",
    description:
      "Connect your existing WhatsApp number in minutes via QR scan. No Facebook Business Manager, no WABA application, no RM0.05/message Meta fees. Bijou handles inbound queries flat at RM299/mo.",
    bullets: [
      "Scan QR → live in 15 min",
      "No per-conversation charges",
      "No Meta markup ever",
    ],
    widget: null,
  },
  {
    icon: <Send className="w-5 h-5" />,
    color: "blue",
    badge: "Live Now",
    title: "Telegram AI Agent",
    subtitle: "Same brain. Second channel. Included free.",
    description:
      "The same AI, knowledge base and Manglish personality runs simultaneously on Telegram at no extra cost. Reach customers on whichever app they prefer.",
    bullets: [
      "Included in Pro — no extra fee",
      "Same TRACE engine and knowledge base",
      "Independent channel, unified setup",
    ],
    widget: null,
  },
  {
    icon: <Brain className="w-5 h-5" />,
    color: "purple",
    badge: "Production · v300 · Live on bijou-production.fly.dev",
    title: "Gemini 2.5 Flash with smart context. Plus automatic handover when AI hits its limit.",
    subtitle: "Fast LLM. Smart escalation. No fake pipeline.",
    description:
      "Every message goes through Gemini 2.5 Flash with per-tenant context, your knowledge base, and Manglish tone. If the conversation gets too complex or emotionally charged, the handover system flags it and a human takes over. No fake pipeline — just a fast LLM and a smart escalation layer that actually works.",
    bullets: [
      "Detects frustration before it escalates",
      "Understands context, not just keywords",
      "Answers only from your data — no hallucination",
    ],
    widget: <TraceWidget />,
  },
  {
    icon: <Languages className="w-5 h-5" />,
    color: "gold",
    badge: "Unique to Bijou",
    title: "Manglish Engine",
    subtitle: "Can lah. Got or not? Sorted.",
    description:
      "20+ regex patterns handle Malaysian code-switching natively — BM, English, Mandarin, Tamil and Manglish blended naturally. Adjust tone from full corporate to full pasar malam.",
    bullets: [
      "English, Malay, Mandarin, Tamil",
      "Tone slider: formal to full Manglish",
      "No robotic 'Certainly, I can assist you'",
    ],
    widget: <ManglishDialWidget />,
  },
  {
    icon: <CalendarCheck className="w-5 h-5" />,
    color: "cyan",
    badge: "Live Now",
    title: "Cal.com Booking",
    subtitle: "Book, check, cancel — all via WhatsApp chat.",
    description:
      "Full two-way calendar integration via Cal.com. Customers book appointments, check availability and cancel — entirely through a WhatsApp or Telegram conversation. No links, no forms.",
    bullets: [
      "Book, check & cancel via chat",
      "Automated email confirmation sent to customer",
      "Zero dev work needed",
    ],
    widget: <CalWidget />,
  },
  {
    icon: <Bell className="w-5 h-5" />,
    color: "amber",
    badge: "Live Now",
    title: "Smart Escalation Alerts",
    subtitle: "You are emailed before the customer rage-quits.",
    description:
      "Bijou detects frustration signals, 3+ unanswered questions and explicit human requests — then instantly emails you the full conversation thread. Never miss a hot lead or angry customer.",
    bullets: [
      "Frustration detection built-in",
      "Full conversation context in alert email",
      "Custom domain email (Growth plan)",
    ],
    widget: <EscalationWidget />,
  },
  {
    icon: <BookOpen className="w-5 h-5" />,
    color: "rose",
    badge: "Live Now",
    title: "Knowledge Base",
    subtitle: "Your FAQs. Your voice. Zero hallucination.",
    description:
      "Upload up to 50 FAQs and 2 documents. Bijou answers only from what you have taught it — no making things up. Update an FAQ and the AI knows instantly, no retraining required.",
    bullets: [
      "50 FAQs + 2 document uploads (Pro)",
      "Instant updates ℔ no retraining",
      "AI stays in-lane, never guesses",
    ],
    widget: null,
  },
  {
    icon: <UserCheck className="w-5 h-5" />,
    color: "emerald",
    badge: "Live Now",
    title: "Lead Qualification",
    subtitle: "Hot, warm, cold ℔ tagged automatically.",
    description:
      "Bijou probes for budget, timeline and intent naturally in conversation. Every lead is tagged automatically so you know exactly who to call back first.",
    bullets: [
      "Budget + timeline detection",
      "Hot / warm / cold tagging",
      "Included in escalation alert summary",
    ],
    widget: null,
  },
  {
    icon: <Shield className="w-5 h-5" />,
    color: "blue",
    badge: "Enterprise-Grade",
    title: "PDPA-Ready Security",
    subtitle: "Your data. Fully isolated. Always.",
    description:
      "Row-Level Security means your customer data is 100% isolated from every other Bijou tenant. AES-256 encryption at rest. PDPA and GDPR compliant. Hosted on Fly.io Singapore region.",
    bullets: [
      "Row-level multi-tenant data isolation",
      "AES-256 + PDPA + GDPR ready",
      "99.9% uptime — Singapore region",
    ],
    widget: <SecurityWidget />,
  },
];

// Color token map (static Tailwind classes ℔ never dynamic)
const colorMap: Record<
  string,
  { icon: string; badge: string; badgeBg: string; glow: string; bullet: string }
> = {
  emerald: {
    icon: "text-emerald-400",
    badge: "text-emerald-400",
    badgeBg: "bg-emerald-500/10 border-emerald-500/20",
    glow: "bg-emerald-500/8",
    bullet: "bg-emerald-400",
  },
  blue: {
    icon: "text-blue-400",
    badge: "text-blue-400",
    badgeBg: "bg-blue-500/10 border-blue-500/20",
    glow: "bg-blue-500/8",
    bullet: "bg-blue-400",
  },
  purple: {
    icon: "text-purple-400",
    badge: "text-purple-400",
    badgeBg: "bg-purple-500/10 border-purple-500/20",
    glow: "bg-purple-500/8",
    bullet: "bg-purple-400",
  },
  gold: {
    icon: "text-yellow-400",
    badge: "text-yellow-400",
    badgeBg: "bg-yellow-500/10 border-yellow-500/20",
    glow: "bg-yellow-500/8",
    bullet: "bg-yellow-400",
  },
  cyan: {
    icon: "text-cyan-400",
    badge: "text-cyan-400",
    badgeBg: "bg-cyan-500/10 border-cyan-500/20",
    glow: "bg-cyan-500/8",
    bullet: "bg-cyan-400",
  },
  amber: {
    icon: "text-amber-400",
    badge: "text-amber-400",
    badgeBg: "bg-amber-500/10 border-amber-500/20",
    glow: "bg-amber-500/8",
    bullet: "bg-amber-400",
  },
  rose: {
    icon: "text-rose-400",
    badge: "text-rose-400",
    badgeBg: "bg-rose-500/10 border-rose-500/20",
    glow: "bg-rose-500/8",
    bullet: "bg-rose-400",
  },
};

interface FeatureDef {
  icon: React.ReactNode;
  color: string;
  badge: string;
  title: string;
  subtitle: string;
  description: string;
  bullets: string[];
  widget: React.ReactNode;
}

const FeatureCard: React.FC<{ feature: FeatureDef; index: number }> = ({
  feature,
  index,
}) => {
  const [open, setOpen] = useState(false);
  const c = colorMap[feature.color] ?? colorMap.emerald!;

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.45, delay: (index % 3) * 0.07 }}
      className="group relative glass-panel-3d rounded-2xl border border-white/[0.07] hover:border-white/20 transition-all duration-300 overflow-hidden"
    >
      <div
        className={`absolute top-0 right-0 w-32 h-32 ${c.glow} rounded-full blur-[60px] pointer-events-none`}
      />

      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left p-5 flex items-start gap-4"
      >
        <div
          className={`flex-shrink-0 w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center ${c.icon}`}
        >
          {feature.icon}
        </div>
        <div className="flex-1 min-w-0">
          <span
            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border mb-1 ${c.badgeBg} ${c.badge}`}
          >
            {feature.badge}
          </span>
          <h3 className="text-sm font-bold text-white leading-tight">
            {feature.title}
          </h3>
          <p className="text-gray-500 text-xs mt-0.5">{feature.subtitle}</p>
        </div>
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.25 }}
          className="flex-shrink-0 mt-1"
        >
          <ChevronDown className="w-4 h-4 text-gray-500" />
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-4">
              <div className="h-px bg-white/5" />
              <p className="text-gray-400 text-sm leading-relaxed">
                {feature.description}
              </p>
              <ul className="space-y-1.5">
                {feature.bullets.map((b, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-2.5 text-sm text-gray-300"
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${c.bullet}`}
                   />
                    {b}
                  </li>
                ))}
              </ul>
              {feature.widget && (
                <div className="bg-black/30 rounded-xl border border-white/5 p-4">
                  {feature.widget}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export const Features: React.FC = () => {
  const { t } = useTranslation();

  const features = [
    {
      icon: <MessageCircle className="w-5 h-5" />,
      color: "emerald",
      badge: t("features.badge.live"),
      title: t("features.wa.title"),
      subtitle: t("features.wa.subtitle"),
      description: t("features.wa.desc"),
      bullets: [t("features.wa.b1"), t("features.wa.b2"), t("features.wa.b3")],
      widget: null,
    },
    {
      icon: <Send className="w-5 h-5" />,
      color: "blue",
      badge: t("features.badge.live"),
      title: t("features.tg.title"),
      subtitle: t("features.tg.subtitle"),
      description: t("features.tg.desc"),
      bullets: [t("features.tg.b1"), t("features.tg.b2"), t("features.tg.b3")],
      widget: null,
    },
    {
      icon: <Brain className="w-5 h-5" />,
      color: "purple",
      // Fix 2 (2026-05-15 code-read): Badge + title downgraded to honest "Gemini Flash + handover" copy.
      // ASI/Humanizer/SRP not imported in bijou.py — only HandoverSystem runs in production.
      badge: t("features.trace.badge"),
      title: t("features.trace.title"),
      subtitle: t("features.trace.subtitle"),
      description: t("features.trace.desc"),
      bullets: [
        t("features.trace.b1"),
        t("features.trace.b2"),
        t("features.trace.b3"),
      ],
      widget: <TraceWidget />,
    },
    {
      icon: <Languages className="w-5 h-5" />,
      color: "gold",
      badge: t("features.badge.unique"),
      title: t("features.manglish.title"),
      subtitle: t("features.manglish.subtitle"),
      description: t("features.manglish.desc"),
      bullets: [
        t("features.manglish.b1"),
        t("features.manglish.b2"),
        t("features.manglish.b3"),
      ],
      widget: <ManglishDialWidget />,
    },
    {
      icon: <CalendarCheck className="w-5 h-5" />,
      color: "cyan",
      badge: t("features.badge.live"),
      title: t("features.cal.title"),
      subtitle: t("features.cal.subtitle"),
      description: t("features.cal.desc"),
      bullets: [
        t("features.cal.b1"),
        t("features.cal.b2"),
        t("features.cal.b3"),
      ],
      widget: <CalWidget />,
    },
    {
      icon: <Bell className="w-5 h-5" />,
      color: "amber",
      badge: t("features.badge.live"),
      title: t("features.escalation.title"),
      subtitle: t("features.escalation.subtitle"),
      description: t("features.escalation.desc"),
      bullets: [
        t("features.escalation.b1"),
        t("features.escalation.b2"),
        t("features.escalation.b3"),
      ],
      widget: <EscalationWidget />,
    },
    {
      icon: <BookOpen className="w-5 h-5" />,
      color: "rose",
      badge: t("features.badge.live"),
      title: t("features.kb.title"),
      subtitle: t("features.kb.subtitle"),
      description: t("features.kb.desc"),
      bullets: [t("features.kb.b1"), t("features.kb.b2"), t("features.kb.b3")],
      widget: null,
    },
    {
      icon: <UserCheck className="w-5 h-5" />,
      color: "emerald",
      badge: t("features.badge.live"),
      title: t("features.leads.title"),
      subtitle: t("features.leads.subtitle"),
      description: t("features.leads.desc"),
      bullets: [
        t("features.leads.b1"),
        t("features.leads.b2"),
        t("features.leads.b3"),
      ],
      widget: null,
    },
    {
      icon: <Shield className="w-5 h-5" />,
      color: "blue",
      badge: t("features.badge.enterprise"),
      title: t("features.security.title"),
      subtitle: t("features.security.subtitle"),
      description: t("features.security.desc"),
      bullets: [
        t("features.security.b1"),
        t("features.security.b2"),
        t("features.security.b3"),
      ],
      widget: <SecurityWidget />,
    },
  ];

  return (
    <section id="features" className="py-24 relative">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/4 w-[500px] h-[500px] bg-emerald-900/6 rounded-full blur-[140px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-900/5 rounded-full blur-[120px]" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <div className="inline-block px-3 py-1 mb-4 rounded-full bg-emerald-500/10 border border-emerald-400/20 text-emerald-400 text-xs font-bold uppercase tracking-wider">
            {t("features.badge")}
          </div>
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            {t("features.title.part1")}{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
             {t("features.title.highlight")}
            </span>
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            {t("features.subtitle")}
          </p>
          <div className="flex items-center justify-center gap-3 mt-5 flex-wrap">
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              {t("features.live")}
            </span>
            <span className="text-gray-600 text-xs">·</span>
            <span className="text-xs text-gray-500">
              {t("features.noBeta")}
            </span>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature, index) => (
            <FeatureCard key={index} feature={feature} index={index} />
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-10 glass-panel-3d rounded-2xl border border-white/[0.07] p-6 md:p-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center"
        >
          {[
            {
              value: "9",
              label: t("features.stats.features"),
              sub: t("features.stats.features.sub"),
            },
            {
              value: "15 min",
              label: t("features.stats.setup"),
              sub: t("features.stats.setup.sub"),
            },
            {
              value: "3,200",
              label: t("features.stats.convos"),
              sub: t("features.stats.convos.sub"),
            },
            {
              value: "4",
              label: t("features.stats.langs"),
              sub: t("features.stats.langs.sub"),
            },
          ].map((stat, i) => (
            <div key={i}>
              <div className="text-2xl md:text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
                {stat.value}
              </div>
              <div className="text-white text-sm font-bold mt-1">
                {stat.label}
              </div>
              <div className="text-gray-500 text-xs mt-0.5">{stat.sub}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};
