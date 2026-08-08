import { motion } from "framer-motion";
import { Check, Minus, X } from "lucide-react";
import React, { useState } from "react";
import { useTranslation } from "react-i18next";

type CellValue = true | false | null | string;

interface Row {
  feature: string;
  category: string;
  bijou: CellValue;
  chatdaddy: CellValue;
  dahreply: CellValue;
  wati: CellValue;
  staff: CellValue;
  highlight?: boolean;
}

const rows: Row[] = [
  // Pricing
  {
    feature: "Monthly Price",
    category: "Pricing",
    bijou: "RM299/mo",
    chatdaddy: "RM75+ (see below)",
    dahreply: "RM499/mo",
    wati: "RM280+",
    staff: "RM1,500–2,500",
    highlight: true,
  },
  {
    feature: "WABA Required",
    category: "Pricing",
    bijou: false,
    chatdaddy: true,
    dahreply: true,
    wati: true,
    staff: false,
  },
  {
    feature: "Hidden Conversation Fees",
    category: "Pricing",
    bijou: false,
    chatdaddy: true,
    dahreply: true,
    wati: "20% markup",
    staff: false,
    highlight: true,
  },
  {
    feature: "Annual Lock-in",
    category: "Pricing",
    bijou: false,
    chatdaddy: true,
    dahreply: false,
    wati: "Some plans",
    staff: "Resignation required",
  },
  {
    feature: "30-Day Money-Back",
    category: "Pricing",
    bijou: true,
    chatdaddy: false,
    dahreply: true,
    wati: false,
    staff: false,
  },

  // Channels
  {
    feature: "WhatsApp (no WABA)",
    category: "Channels",
    bijou: true,
    chatdaddy: false,
    dahreply: false,
    wati: false,
    staff: true,
    highlight: true,
  },
  {
    feature: "Telegram",
    category: "Channels",
    bijou: true,
    chatdaddy: false,
    dahreply: false,
    wati: false,
    staff: true,
    highlight: true,
  },
  {
    feature: "Facebook Messenger",
    category: "Channels",
    bijou: "Q3 2026",
    chatdaddy: true,
    dahreply: "Partial",
    wati: false,
    staff: true,
  },

  // AI & Language
  {
    feature: "Manglish / Malaysian AI",
    category: "AI & Language",
    bijou: true,
    chatdaddy: false,
    dahreply: "Partial",
    wati: false,
    staff: "If Malaysian",
    highlight: true,
  },
  {
    feature: "English + BM + 中文 + தமிழ்",
    category: "AI & Language",
    bijou: true,
    chatdaddy: "English only",
    dahreply: "Partial",
    wati: "English only",
    staff: true,
  },
  {
    feature: "No-hallucination KB",
    category: "AI & Language",
    bijou: true,
    chatdaddy: false,
    dahreply: "Basic",
    wati: false,
    staff: "Depends",
  },
  {
    feature: "Emotion & Frustration Detection",
    category: "AI & Language",
    bijou: true,
    chatdaddy: false,
    dahreply: false,
    wati: false,
    staff: true,
  },

  // Automation
  {
    feature: "Cal.com Calendar Booking",
    category: "Automation",
    bijou: true,
    chatdaddy: "Via Zapier",
    dahreply: "Basic",
    wati: "Via Zapier",
    staff: "Manual",
    highlight: true,
  },
  {
    feature: "Auto Email Booking Confirm",
    category: "Automation",
    bijou: true,
    chatdaddy: false,
    dahreply: "Partial",
    wati: false,
    staff: "Manual",
  },
  {
    feature: "Escalation Email Alerts",
    category: "Automation",
    bijou: true,
    chatdaddy: false,
    dahreply: false,
    wati: false,
    staff: true,
  },
  {
    feature: "Lead Qualification Tags",
    category: "Automation",
    bijou: true,
    chatdaddy: "Basic",
    dahreply: "Basic",
    wati: false,
    staff: "Manual",
  },

  // Setup & Support
  {
    feature: "Setup Time",
    category: "Setup & Support",
    bijou: "15 minutes",
    chatdaddy: "2–3 days",
    dahreply: "1 week+",
    wati: "2–3 days",
    staff: "2 weeks hiring",
    highlight: true,
  },
  {
    feature: "Self-Serve (No Dev)",
    category: "Setup & Support",
    bijou: true,
    chatdaddy: false,
    dahreply: false,
    wati: false,
    staff: false,
  },
  {
    feature: "Human Support",
    category: "Setup & Support",
    bijou: "WhatsApp direct",
    chatdaddy: false,
    dahreply: "Slow",
    wati: "Slow",
    staff: true,
  },
  {
    feature: "ROI Payback Period",
    category: "Setup & Support",
    bijou: "~8 days",
    chatdaddy: "Unknown",
    dahreply: "3–6 mo",
    wati: "3–6 mo",
    staff: "Never",
  },
];

const categories = ["All", ...Array.from(new Set(rows.map((r) => r.category)))];

const providers = [
  { key: "bijou", label: "Bijou PRO", price: "RM299/mo", highlight: true },
  { key: "chatdaddy", label: "ChatDaddy", price: "RM75+*" },
  { key: "dahreply", label: "DahReply", price: "RM499/mo" },
  { key: "wati", label: "Wati", price: "RM280+" },
  { key: "staff", label: "Human Staff", price: "RM1,500+" },
];

const Cell: React.FC<{ value: CellValue; isBijou?: boolean }> = ({
  value,
  isBijou,
}) => {
  if (value === true)
    return (
      <Check
        className={`w-4 h-4 mx-auto ${isBijou ? "text-emerald-400" : "text-gray-400"}`}
      />
    );
  if (value === false) return <X className="w-4 h-4 mx-auto text-red-400/60" />;
  if (value === null)
    return <Minus className="w-4 h-4 mx-auto text-gray-600" />;
  return (
    <span
      className={`text-xs font-medium leading-tight ${isBijou ? "text-emerald-300 font-bold" : "text-gray-400"}`}
    >
      {value}
    </span>
  );
};

export const ComparisonTable: React.FC = () => {
  const { t } = useTranslation();
  const [activeCategory, setActiveCategory] = useState(
    t("comparison.filter.all"),
  );

  const categoryKeys: Record<string, string> = {
    Pricing: t("comparison.cat.pricing"),
    Channels: t("comparison.cat.channels"),
    "AI & Language": t("comparison.cat.ai"),
    Automation: t("comparison.cat.automation"),
    "Setup & Support": t("comparison.cat.setup"),
  };

  const rawCategories = [
    "All",
    ...Array.from(new Set(rows.map((r) => r.category))),
  ];
  const localizedCategories = rawCategories.map((c) =>
    c === "All" ? t("comparison.filter.all") : (categoryKeys[c] ?? c),
  );

  const visible =
    activeCategory === t("comparison.filter.all")
      ? rows
      : rows.filter(
          (r) => (categoryKeys[r.category] ?? r.category) === activeCategory,
        );

  return (
    <section id="comparison" className="py-24 relative">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 right-1/4 w-[500px] h-[400px] bg-red-900/5 rounded-full blur-[140px]" />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[300px] bg-emerald-900/5 rounded-full blur-[120px]" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <div className="inline-block px-3 py-1 mb-4 rounded-full bg-rose-500/10 border border-rose-400/20 text-rose-400 text-xs font-bold uppercase tracking-wider">
            {t("comparison.badge")}
          </div>
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            {t("comparison.title.part1")}{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 to-orange-400">
              {t("comparison.title.highlight")}
            </span>
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            {t("comparison.subtitle")}
          </p>

          {/* Disclaimer on ChatDaddy asterisk */}
          <div className="mt-4 inline-block px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <p className="text-amber-400 text-xs">
              {t("comparison.disclaimer")}
            </p>
          </div>
        </motion.div>

        {/* Category filter */}
        <div className="flex flex-wrap gap-2 justify-center mb-8">
          {localizedCategories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                activeCategory === cat
                  ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
                  : "bg-white/5 border-white/10 text-gray-400 hover:border-white/20"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Table wrapper — horizontal scroll on mobile */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5 }}
          className="glass-panel-3d rounded-2xl border border-white/[0.08] overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px]">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left px-5 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider w-48">
                    Feature
                  </th>
                  {providers.map((p) => (
                    <th
                      key={p.key}
                      className={`px-4 py-4 text-center ${p.highlight ? "bg-emerald-500/5" : ""}`}
                    >
                      <div
                        className={`text-sm font-bold ${p.highlight ? "text-emerald-400" : "text-gray-300"}`}
                      >
                        {p.highlight && (
                          <span className="block text-[10px] font-black uppercase tracking-widest text-emerald-500 mb-0.5">
                            {t("comparison.best")}
                          </span>
                        )}
                        {p.label}
                      </div>
                      <div
                        className={`text-xs mt-0.5 ${p.highlight ? "text-emerald-300 font-bold" : "text-gray-500"}`}
                      >
                        {p.price}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visible.map((row, i) => {
                  // Category divider
                  const prevCat = i > 0 ? visible[i - 1]?.category : null;
                  const showDivider = prevCat && prevCat !== row.category;
                  return (
                    <React.Fragment key={i}>
                      {showDivider && (
                        <tr>
                          <td colSpan={6} className="px-5 py-2 bg-white/[0.02]">
                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-600">
                              {categoryKeys[row.category] ?? row.category}
                            </span>
                          </td>
                        </tr>
                      )}
                      {i === 0 && (
                        <tr>
                          <td colSpan={6} className="px-5 py-2 bg-white/[0.02]">
                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-600">
                              {categoryKeys[row.category] ?? row.category}
                            </span>
                          </td>
                        </tr>
                      )}
                      <motion.tr
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: i * 0.03 }}
                        className={`border-b border-white/[0.04] transition-colors hover:bg-white/[0.02] ${row.highlight ? "bg-emerald-500/[0.02]" : ""}`}
                      >
                        <td className="px-5 py-3.5">
                          <span
                            className={`text-sm ${row.highlight ? "text-white font-semibold" : "text-gray-400"}`}
                          >
                            {row.feature}
                          </span>
                        </td>
                        {providers.map((p) => (
                          <td
                            key={p.key}
                            className={`px-4 py-3.5 text-center ${p.highlight ? "bg-emerald-500/[0.04]" : ""}`}
                          >
                            <Cell
                              value={row[p.key as keyof Row] as CellValue}
                              isBijou={p.highlight}
                            />
                          </td>
                        ))}
                      </motion.tr>
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Bottom CTA */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-10 glass-panel-3d rounded-2xl p-8 border border-white/10 text-center"
        >
          <p className="text-white text-xl font-bold mb-2">
            {t("comparison.cta.title")}
          </p>
          <p className="text-gray-400 text-sm mb-6 max-w-xl mx-auto">
            {t("comparison.cta.body")}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <a
              href="https://api.whatsapp.com/send/?phone=60174106981&text=Hi+Jewel+I+saw+the+comparison+table+and+want+to+know+more+about+Bijou"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-bold text-sm bg-emerald-500 hover:bg-emerald-400 text-black transition-all shadow-[0_0_30px_rgba(16,185,129,0.35)]"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
              </svg>
              {t("comparison.cta.wa")}
            </a>
            <a
              href="mailto:jewel@mybijou.xyz"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-bold text-sm bg-white/5 border border-white/10 text-gray-300 hover:border-white/20 hover:text-white transition-all"
            >
              {t("comparison.cta.email")}
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
};
