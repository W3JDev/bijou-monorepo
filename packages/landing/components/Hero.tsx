import { motion } from "framer-motion";
import {
    AlertTriangle,
    Calendar,
    ExternalLink,
    ShieldCheck,
    Users,
} from "lucide-react";
import React from "react";
import { useTranslation } from "react-i18next";
import { trackDemoBooking, trackTrialSignup } from "../utils/analytics";
import { BijouLogo } from "./BijouLogo";

interface HeroProps {
  onOpenModal: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onOpenModal }) => {
  const { t, i18n } = useTranslation();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: "spring" as const,
        stiffness: 100,
        damping: 10,
      },
    },
  };

  return (
    <section className="relative pt-24 pb-24 lg:pt-48 lg:pb-48 overflow-hidden">
      {/* Enhanced Background Effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-[120px] animate-pulse-slow" />
        <div
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/15 rounded-full blur-[120px] animate-pulse-slow"
          style={{ animationDelay: "2s" }}
        />
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-400/5 rounded-full blur-[150px]" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-8 items-center">
          {/* Text Content */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="text-center lg:text-left"
          >
            <motion.div
              variants={itemVariants}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass-panel-3d border-2 border-gold-400/50 text-gold-300 text-xs font-bold tracking-wider mb-8 uppercase shadow-[0_0_30px_rgba(212,175,55,0.4)] animate-pulse bg-gold-500/10"
            >
              <span className="w-2 h-2 rounded-full bg-gold-400 animate-pulse shadow-[0_0_15px_#D4AF37]" />
              {t("hero.badge")}
            </motion.div>

            <motion.h1
              variants={itemVariants}
              className="text-5xl sm:text-6xl lg:text-8xl font-display font-extrabold tracking-tight leading-[1.08] mb-6 lg:mb-8"
            >
              <span className="block">
                {t("hero.title.part1")}{" "}
                <span className="text-gradient-gold">
                  {t("hero.title.savingsAmount")}
                </span>
              </span>
              <span className="block">
                {t("hero.title.part2")}{" "}
                <span className="text-gradient-premium">
                  {t("hero.title.priceAmount")}
                </span>
              </span>
            </motion.h1>

            <motion.p
              variants={itemVariants}
              className="text-xl text-gray-300 mb-12 max-w-2xl mx-auto lg:mx-0 leading-relaxed font-light"
            >
              {t("hero.subtitle.part1")}{" "}
              <span className="text-gold-400 font-bold">
                {t("hero.subtitle.roi")}
              </span>{" "}
              {t("hero.subtitle.part2")}
            </motion.p>

            <motion.div variants={itemVariants} className="mb-12">
              {/* Lead Capture Tabs */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4 mb-4">
                <a
                  href="https://app.mybijou.xyz/signup"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => trackTrialSignup(i18n.language)}
                  className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all bg-gradient-to-r from-gold-500 to-gold-300 text-black shadow-[0_0_20px_rgba(212,175,55,0.4)] hover:shadow-[0_0_30px_rgba(212,175,55,0.6)] hover:scale-[1.02]"
                >
                  <Users className="w-5 h-5" />
                  {t("hero.cta.trial")}
                  <ExternalLink className="w-4 h-4 opacity-70" />
                </a>

                <a
                  href="https://cal.com/getbijou"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => trackDemoBooking(i18n.language)}
                  className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all glass-panel-3d text-white border-gold-400/30 hover:border-gold-400/60 hover:bg-gold-400/5 hover:scale-[1.02]"
                >
                  <Calendar className="w-5 h-5" />
                  {t("hero.cta.demo")}
                </a>
              </div>

              {/* Stop The Bleeding — pain-point secondary CTA */}
              <a
                href="#revenue"
                className="inline-flex items-center gap-2 text-sm font-bold text-red-400 hover:text-red-300 transition-colors group/bleed"
              >
                <AlertTriangle className="w-4 h-4 animate-pulse" />
                Still losing leads every night? See how much it's costing you
                <span className="group-hover/bleed:translate-x-1 transition-transform inline-block">
                  →
                </span>
              </a>

              <p className="text-sm text-gray-400 text-center lg:text-left">
                {t("hero.trustFooter")}
              </p>
            </motion.div>

            {/* Compliance Badge */}
            <motion.div
              variants={itemVariants}
              className="pt-8 border-t border-white/10"
            >
              <div className="flex items-center justify-center lg:justify-start gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <span className="text-xs text-emerald-400 font-semibold tracking-wide">
                  {t("hero.trust.pdpa")}
                </span>
              </div>
            </motion.div>
          </motion.div>

          {/* 3D Visual / Illustration */}
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
              duration: 1,
              delay: 0.4,
              type: "spring",
              stiffness: 50,
            }}
            className="relative lg:h-[600px] flex items-center justify-center perspective-1000 hidden lg:flex"
          >
            {/* Background Glows */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-[100px]" />

            {/* Abstract 3D Representation */}
            <div className="relative w-full max-w-md aspect-square animate-float transform preserve-3d">
              {/* Phone Frame - Enhanced 3D Look */}
              <div className="absolute inset-0 bg-gradient-to-br from-gray-800 to-black rounded-[3rem] border-4 border-gray-700/50 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8),inset_0_2px_4px_rgba(255,255,255,0.3)] overflow-hidden glass-panel-3d backdrop-blur-3xl ring-1 ring-white/10">
                {/* Screen Content */}
                <div className="p-6 h-full flex flex-col bg-gradient-to-b from-dark-900 to-black relative z-10">
                  {/* Header */}
                  <div className="flex items-center gap-4 mb-8 pb-4 border-b border-white/5">
                    <div className="relative">
                      <div className="w-12 h-12 rounded-xl bg-deep-green-500/40 flex items-center justify-center shadow-[0_0_20px_rgba(227,180,87,0.35)] border border-gold-400/30">
                        <BijouLogo size={32} tone="gold" />
                      </div>
                      <div className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-emerald-400 rounded-full border-2 border-black shadow-[0_0_8px_rgba(74,222,128,0.6)]" />
                    </div>
                    <div>
                      <div className="font-bold text-white text-lg tracking-tight">
                        {t("hero.chatDemo.assistant")}
                      </div>
                      <div className="text-xs text-emerald-400 font-medium tracking-wide flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                        {t("hero.chatDemo.status")}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-6 flex-1">
                    {/* Message 1 */}
                    <div className="glossy-pill p-4 rounded-2xl rounded-tl-none max-w-[85%] self-start">
                      <p className="text-sm text-gray-200">
                        {t("hero.chatDemo.msg1")}
                      </p>
                    </div>

                    {/* Message 2 (Bijou) */}
                    <div className="glossy-pill-emerald p-4 rounded-2xl rounded-tr-none max-w-[85%] ml-auto">
                      <p className="text-sm text-emerald-100 font-medium">
                        {t("hero.chatDemo.msg2")}
                      </p>
                    </div>

                    {/* Message 3 */}
                    <div className="glossy-pill p-4 rounded-2xl rounded-tl-none max-w-[85%] self-start">
                      <p className="text-sm text-gray-200">
                        {t("hero.chatDemo.msg3")}
                      </p>
                    </div>

                    {/* Message 4 (Bijou) */}
                    <div className="glossy-pill-emerald p-4 rounded-2xl rounded-tr-none max-w-[85%] ml-auto">
                      <p className="text-sm text-emerald-100 font-medium">
                        {t("hero.chatDemo.msg4")}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating ROI Card - Repositioned to Top Right Corner */}
              <div className="absolute -right-8 -top-8 glass-panel-3d p-4 rounded-2xl flex flex-col gap-1 animate-pulse-slow shadow-2xl border border-gold-400/30 backdrop-blur-xl bg-deep-green-500/80 max-w-[200px]">
                <div className="text-xs text-gold-300 uppercase font-bold">
                  {t("hero.roiCard.title")}
                </div>
                <div className="text-3xl font-bold text-gold-400">
                  {t("hero.roiCard.amount")}
                </div>
                <div className="text-[10px] text-gray-300">
                  {t("hero.roiCard.comparison")}
                </div>
                <div className="w-full bg-deep-green-600 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div className="bg-gold-400 h-full w-[95%] shadow-[0_0_8px_rgba(212,175,55,0.6)]"></div>
                </div>
                <div className="text-xs text-gold-300 mt-1 font-semibold">
                  {t("hero.roiCard.roi")}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
