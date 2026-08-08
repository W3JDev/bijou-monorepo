import { motion } from "framer-motion";
import { ArrowUpRight, Building2, Stethoscope } from "lucide-react";
import React from "react";
import { useTranslation } from "react-i18next";

interface CaseStudiesProps {
  onOpenModal: () => void;
}

export const CaseStudies: React.FC<CaseStudiesProps> = ({ onOpenModal }) => {
  const { t } = useTranslation();

  return (
    <section id="case-studies" className="py-24 bg-black/40 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            {t("cases.title")}
          </h2>
          <p className="text-gray-400 text-lg">{t("cases.subtitle")}</p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-10">
          {/* Real Estate Case Study */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="glass-panel-3d p-10 rounded-3xl group relative"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-[80px] group-hover:bg-blue-500/20 transition-colors" />

            <div className="flex items-center gap-5 mb-10 relative z-10">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.15)]">
                <Building2 className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-white">
                  {t("cases.realEstate.company")}
                </h3>
                <p className="text-sm text-gray-400 font-medium">
                  {t("cases.realEstate.industry")}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-5 mb-10 relative z-10">
              <div className="bg-white/5 p-5 rounded-2xl border border-white/5">
                <div className="text-4xl font-bold text-white mb-2">
                  {t("cases.realEstate.stat1.value")}
                </div>
                <div className="text-xs text-gray-400 uppercase tracking-widest font-semibold">
                  {t("cases.realEstate.stat1.label")}
                </div>
              </div>
              <div className="bg-gold-900/20 p-5 rounded-2xl border border-gold-400/20 shadow-[0_4px_20px_rgba(212,175,55,0.1)]">
                <div className="text-4xl font-bold text-gold-400 mb-2">
                  {t("cases.realEstate.stat2.value")}
                </div>
                <div className="text-xs text-gold-200/70 uppercase tracking-widest font-semibold">
                  {t("cases.realEstate.stat2.label")}
                </div>
              </div>
            </div>

            <div className="space-y-6 relative z-10">
              <p className="text-gray-300 italic text-lg leading-relaxed">
                {t("cases.realEstate.quote")}
              </p>
              <button
                onClick={onOpenModal}
                className="flex items-center gap-2 text-sm text-blue-400 font-bold hover:gap-3 transition-all group/btn"
              >
                {t("cases.realEstate.cta")}{" "}
                <ArrowUpRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
              </button>
            </div>
          </motion.div>

          {/* Healthcare Case Study */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="glass-panel-3d p-10 rounded-3xl group relative"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-orange-500/10 rounded-full blur-[80px] group-hover:bg-orange-500/20 transition-colors" />

            <div className="flex items-center gap-5 mb-10 relative z-10">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-orange-500/20 to-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400 shadow-[0_0_20px_rgba(249,115,22,0.15)]">
                <Stethoscope className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-white">
                  {t("cases.healthcare.company")}
                </h3>
                <p className="text-sm text-gray-400 font-medium">
                  {t("cases.healthcare.industry")}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-5 mb-10 relative z-10">
              <div className="bg-white/5 p-5 rounded-2xl border border-white/5">
                <div className="text-4xl font-bold text-white mb-2">
                  {t("cases.healthcare.stat1.value")}
                </div>
                <div className="text-xs text-gray-400 uppercase tracking-widest font-semibold">
                  {t("cases.healthcare.stat1.label")}
                </div>
              </div>
              <div className="bg-orange-900/20 p-5 rounded-2xl border border-orange-500/20 shadow-[0_4px_20px_rgba(249,115,22,0.1)]">
                <div className="text-4xl font-bold text-orange-400 mb-2">
                  {t("cases.healthcare.stat2.value")}
                </div>
                <div className="text-xs text-orange-200/70 uppercase tracking-widest font-semibold">
                  {t("cases.healthcare.stat2.label")}
                </div>
              </div>
            </div>

            <div className="space-y-6 relative z-10">
              <p className="text-gray-300 italic text-lg leading-relaxed">
                {t("cases.healthcare.quote")}
              </p>
              <button
                onClick={onOpenModal}
                className="flex items-center gap-2 text-sm text-orange-400 font-bold hover:gap-3 transition-all group/btn"
              >
                {t("cases.healthcare.cta")}{" "}
                <ArrowUpRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
