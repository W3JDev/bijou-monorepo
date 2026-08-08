import { AnimatePresence, motion } from "framer-motion";
import { Download, Smartphone, X } from "lucide-react";
import React, { useEffect, useState } from "react";

interface PWAInstallPromptProps {
  className?: string;
}

export const PWAInstallPrompt: React.FC<PWAInstallPromptProps> = ({
  className = "",
}) => {
  const [showPrompt, setShowPrompt] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);

  useEffect(() => {
    // Check if running in standalone mode (already installed)
    setIsStandalone(window.matchMedia("(display-mode: standalone)").matches);

    // Check if iOS device
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    setIsIOS(iOS);

    // Listen for install prompt
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      if (!isStandalone) {
        setShowPrompt(true);
      }
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);

    // Show iOS install instructions after delay
    if (
      iOS &&
      !isStandalone &&
      !localStorage.getItem("bijou-ios-install-dismissed")
    ) {
      setTimeout(() => setShowPrompt(true), 3000);
    }

    return () => {
      window.removeEventListener(
        "beforeinstallprompt",
        handleBeforeInstallPrompt,
      );
    };
  }, [isStandalone]);

  const handleInstall = async () => {
    if (isIOS) {
      // iOS install instructions
      setShowPrompt(false);
      return;
    }

    // PWA install for other browsers
    try {
      if ((window as any).installBijouPWA) {
        await (window as any).installBijouPWA();
        setShowPrompt(false);
      }
    } catch (error) {
      console.error("Failed to install PWA:", error);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    if (isIOS) {
      localStorage.setItem("bijou-ios-install-dismissed", "true");
    }
  };

  // Don't show if already installed or prompt not ready
  if (isStandalone || !showPrompt) {
    return null;
  }

  return (
    <div
      className={`fixed left-4 right-4 z-50 ${className}`}
      style={{ bottom: "calc(env(safe-area-inset-bottom, 0px) + 80px)" }}
    >
      <AnimatePresence>
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          className="bg-gradient-to-r from-emerald-900 to-green-900 backdrop-blur-xl border border-emerald-400/20 rounded-2xl shadow-2xl max-w-sm mx-auto"
        >
          <div className="p-4 relative">
            {/* Close button */}
            <button
              onClick={handleDismiss}
              className="absolute top-3 right-3 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-white/70 hover:text-white hover:bg-white/20 transition-all"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-start gap-3 pr-8">
              <div className="w-12 h-12 bg-emerald-400/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <Smartphone className="w-6 h-6 text-emerald-400" />
              </div>

              <div className="flex-1 min-w-0">
                <h4 className="text-white font-bold text-lg mb-1">
                  Install Bijou AI
                </h4>
                <p className="text-white/80 text-sm mb-4">
                  {isIOS
                    ? "Add to Home Screen for easy access to your Manglish digital employee!"
                    : "Install as an app for faster access and offline features!"}
                </p>

                {isIOS ? (
                  <div className="text-white/70 text-xs space-y-2 mb-4">
                    <p>📱 Tap the Share button</p>
                    <p>➕ Select "Add to Home Screen"</p>
                    <p>✅ Confirm to install</p>
                  </div>
                ) : (
                  <motion.button
                    onClick={handleInstall}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-white font-semibold py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Install App
                  </motion.button>
                )}

                {!isIOS && (
                  <p className="text-white/50 text-xs mt-2 text-center">
                    Works offline • Fast loading • Native feel
                  </p>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
