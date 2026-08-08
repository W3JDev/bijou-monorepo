import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Clock, MessageCircle, X } from "lucide-react";
import React, { useEffect, useState } from "react";
import { track as trackPostHog } from "../services/posthog";

interface WhatsAppCTAProps {
  phoneNumber?: string;
  className?: string;
}

export const WhatsAppCTA: React.FC<WhatsAppCTAProps> = ({
  phoneNumber = "60174106981",
  className = "",
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);

  // Show CTA after user scrolls or after delay
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 200) {
        setIsVisible(true);
      }
    };

    const timer = setTimeout(() => {
      setIsVisible(true);
    }, 3000); // Show after 3 seconds

    window.addEventListener("scroll", handleScroll);
    return () => {
      window.removeEventListener("scroll", handleScroll);
      clearTimeout(timer);
    };
  }, []);

  // Auto-expand only on desktop, only once, after a delay — never on mobile
  useEffect(() => {
    if (isVisible && !hasInteracted && window.innerWidth >= 768) {
      const expandTimer = setTimeout(() => {
        setIsExpanded(true);
        setTimeout(() => setIsExpanded(false), 5000);
      }, 5000); // Show once after 5s on desktop only

      return () => clearTimeout(expandTimer);
    }
    return; // explicit void when guard doesn't fire
  }, [isVisible, hasInteracted]);

  const handleClick = () => {
    setHasInteracted(true);

    // Track the click (optional - removed to prevent 500 errors)
    // We can track this via analytics later if needed

    // Generate contextual message based on time
    const hour = new Date().getHours();
    let message = "";

    if (hour >= 9 && hour < 18) {
      message =
        "Hi! Saw your Bijou AI website. Can you show me how it works for my business?";
    } else {
      message =
        "Hi! Interested in Bijou AI. Can we chat tomorrow about how it can help my late-night leads?";
    }

    // Open WhatsApp
    const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(message)}`;
    window.open(whatsappUrl, "_blank", "noopener,noreferrer");
    // PostHog: track the WA handoff (don't PII the number)
    trackPostHog("whatsapp_cta_clicked", {
      from: "floating_cta",
      hour_bucket: hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening",
    });
  };

  const handleExpand = () => {
    setIsExpanded(!isExpanded);
    setHasInteracted(true);
  };

  if (!isVisible) return null;

  return (
    <div
      className={`hidden sm:block fixed right-4 z-50 ${className}`}
      style={{ bottom: "calc(env(safe-area-inset-bottom, 0px) + 16px)" }}
    >
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.8 }}
            className="absolute bottom-20 right-0 w-64 sm:w-80 max-w-[85vw] p-4 sm:p-6 glass-panel-3d rounded-2xl border border-emerald-500/30 bg-[#050816]/95 backdrop-blur-xl shadow-2xl"
          >
            <button
              onClick={() => setIsExpanded(false)}
              className="absolute top-3 right-3 w-6 h-6 rounded-full glass-panel flex items-center justify-center hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center">
                <MessageCircle className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h4 className="text-white font-semibold">
                  Chat with Bijou Team
                </h4>
                <div className="flex items-center gap-2 text-green-400 text-sm">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  <Clock className="w-3 h-3" />
                  Online now
                </div>
              </div>
            </div>

            <p className="text-gray-300 text-xs sm:text-sm mb-4 leading-relaxed">
              Get instant answers from our Malaysian team. We speak your
              language! 🇲🇾
            </p>

            <motion.button
              onClick={handleClick}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full flex items-center justify-center gap-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-semibold py-4 px-6 rounded-xl shadow-[0_0_20px_rgba(34,197,94,0.4)] hover:shadow-[0_0_30px_rgba(34,197,94,0.6)] transition-all"
            >
              <MessageCircle className="w-5 h-5" />
              Start WhatsApp Chat
              <ArrowRight className="w-4 h-4" />
            </motion.button>

            <p className="text-xs text-gray-400 text-center mt-3">
              Usually replies within 5 minutes
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main CTA Button */}
      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={handleExpand}
        className="relative w-14 h-14 sm:w-16 sm:h-16 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full shadow-[0_0_30px_rgba(34,197,94,0.4)] hover:shadow-[0_0_40px_rgba(34,197,94,0.6)] transition-all flex items-center justify-center group"
      >
        {/* Pulse animation */}
        <div className="absolute inset-0 rounded-full bg-green-500/30 animate-ping"></div>

        <MessageCircle className="w-8 h-8 text-white relative z-10 group-hover:scale-110 transition-transform" />

        {/* Notification badge */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold border-2 border-white"
        >
          1
        </motion.div>
      </motion.button>

      {/* Quick access to direct WhatsApp */}
      <motion.button
        onClick={handleClick}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="absolute bottom-20 right-0 px-4 py-2 glass-panel-3d rounded-full text-green-400 text-sm font-medium hover:bg-green-500/10 transition-all opacity-0 group-hover:opacity-100"
      >
        Quick Chat
      </motion.button>
    </div>
  );
};
