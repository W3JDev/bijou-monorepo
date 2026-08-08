import { AnimatePresence, motion } from "framer-motion";
import {
    ArrowRight,
    Calendar,
    MessageSquare,
    User,
    X,
    Zap,
} from "lucide-react";
import React, { useState } from "react";
import { LeadCaptureForm } from "./LeadCaptureForm";
import { track as trackPostHog } from "../services/posthog";

interface FinalCTAProps {
  onOpenModal?: () => void;
  onOpenSlideDeck?: () => void;
}

export const FinalCTA: React.FC<FinalCTAProps> = ({
  onOpenModal,
  onOpenSlideDeck,
}) => {
  const [showModal, setShowModal] = useState(false);
  return (
    <section className="py-24 relative overflow-hidden border-t border-white/5 bg-dark-900">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gold-900/20 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        <h2 className="text-4xl md:text-6xl font-display font-extrabold mb-6 tracking-tight">
          Ready to Stop Losing Leads?
        </h2>
        <p className="text-xl text-gray-300 mb-10 font-light">
          Start free — RM0. 30-day money-back. No credit card. Cancel anytime.
        </p>

        <button
          onClick={() => { trackPostHog("hero_cta_clicked", { cta: "start_free_trial_final" }); setShowModal(true); }}
          className="inline-flex items-center gap-3 bg-gradient-to-r from-gold-500 to-gold-300 hover:from-gold-400 hover:to-gold-300 text-black font-bold py-5 px-12 rounded-xl shadow-[0_0_30px_rgba(212,175,55,0.4)] hover:shadow-[0_0_50px_rgba(212,175,55,0.6)] transition-all transform hover:scale-[1.02] text-xl mb-4"
        >
          Start Free Trial
          <ArrowRight className="w-6 h-6" />
        </button>

        {onOpenSlideDeck && (
          <div className="mb-16">
            <button
              onClick={() => { trackPostHog("slide_deck_opened", { from: "final_cta" }); onOpenSlideDeck?.(); }}
              className="text-sm text-gray-500 hover:text-gold-400 transition-colors underline underline-offset-4"
            >
              Not ready yet? Get our pitch deck &amp; user guide →
            </button>
          </div>
        )}

        <div className="grid md:grid-cols-3 gap-8 text-left border-t border-white/10 pt-12">
          <div>
            <h4 className="font-bold text-white mb-2 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-gold-400" />
              What happens after the trial?
            </h4>
            <p className="text-sm text-gray-400 leading-relaxed">
              It's RM299/month (or RM2,990/year). You can cancel anytime with
              one click. No long-term contracts.
            </p>
          </div>
          <div>
            <h4 className="font-bold text-white mb-2 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-gold-400" />
              Do I need technical skills?
            </h4>
            <p className="text-sm text-gray-400 leading-relaxed">
              No. If you can scan a QR code and upload a PDF, you can set up
              Bijou in 5 minutes.
            </p>
          </div>
          <div>
            <h4 className="font-bold text-white mb-2 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-gold-400" />
              Can I switch back to manual?
            </h4>
            <p className="text-sm text-gray-400 leading-relaxed">
              Yes, anytime. You can pause Bijou or jump into any conversation to
              take over manually.
            </p>
          </div>
        </div>
      </div>

      {/* Onboarding Choice Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className="glass-panel-3d bg-dark-900/95 border border-white/10 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)] relative max-w-4xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close button */}
              <button
                onClick={() => setShowModal(false)}
                className="absolute top-6 right-6 w-10 h-10 rounded-full glass-panel flex items-center justify-center hover:bg-white/10 transition-colors z-10"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>

              <div className="p-8">
                <div className="text-center mb-8">
                  <h3 className="text-3xl font-display font-bold mb-4">
                    Choose Your Path
                  </h3>
                  <p className="text-gray-300 text-lg">
                    How would you like to get started with Bijou AI?
                  </p>
                </div>

                <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
                  {/* Direct Trial Option */}
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="glass-panel-3d p-8 rounded-2xl border border-gold-400/30 bg-gold-900/10 relative group"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-full bg-gold-500/20 flex items-center justify-center">
                        <Zap className="w-6 h-6 text-gold-400" />
                      </div>
                      <div>
                        <h4 className="text-xl font-bold text-white">
                          Quick Start Trial
                        </h4>
                        <p className="text-gold-400 text-sm">
                          Get instant access
                        </p>
                      </div>
                    </div>

                    <p className="text-gray-300 mb-6 leading-relaxed">
                      Start free at RM0 — no credit card, no WABA required. Get
                      set up in minutes and test Bijou with your leads
                      immediately.
                    </p>

                    <div className="space-y-2 text-sm text-gray-400 mb-6">
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-gold-400" />
                        5-minute setup process
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-gold-400" />
                        Instant WhatsApp integration
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-gold-400" />
                        30-day money-back guarantee
                      </div>
                    </div>

                    <LeadCaptureForm
                      source="final_cta_direct"
                      className="space-y-4"
                      onSuccess={() => {
                        setShowModal(false);
                        window.location.href = "https://app.mybijou.xyz/signup";
                      }}
                    />
                  </motion.div>

                  {/* Guided Onboarding Option */}
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="glass-panel-3d p-8 rounded-2xl border border-blue-500/30 bg-blue-900/10 relative group"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <Calendar className="w-6 h-6 text-blue-400" />
                      </div>
                      <div>
                        <h4 className="text-xl font-bold text-white">
                          Guided Onboarding
                        </h4>
                        <p className="text-blue-400 text-sm">
                          Personalized setup
                        </p>
                      </div>
                    </div>

                    <p className="text-gray-300 mb-6 leading-relaxed">
                      Book a 15-min demo call. We'll analyze your business,
                      optimize your setup, and show you advanced strategies.
                    </p>

                    <div className="space-y-2 text-sm text-gray-400 mb-6">
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                        Free business analysis
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                        Custom lead optimization
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                        Advanced playbook setup
                      </div>
                    </div>

                    <a
                      href="https://cal.com/getbijou"
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => setShowModal(false)}
                      className="w-full bg-blue-500 hover:bg-blue-400 text-white font-bold py-4 px-6 rounded-xl transition-all flex items-center justify-center gap-2 group-hover:scale-105"
                    >
                      <User className="w-5 h-5" />
                      Book Your Demo Call
                    </a>

                    <p className="text-xs text-gray-400 text-center mt-3">
                      Available slots: Today & Tomorrow
                    </p>
                  </motion.div>
                </div>

                <div className="mt-8 pt-6 border-t border-white/10 text-center">
                  <p className="text-sm text-gray-400 mb-3">
                    Questions? WhatsApp our team directly
                  </p>
                  <a
                    href="https://wa.me/60174106981?text=Hi! I'm interested in Bijou AI. Can we chat about how it can help my business?"
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => setShowModal(false)}
                    className="inline-flex items-center gap-2 text-gold-400 hover:text-gold-300 transition-colors font-medium"
                  >
                    <MessageSquare className="w-4 h-4" />
                    Chat with us on WhatsApp
                  </a>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
};
