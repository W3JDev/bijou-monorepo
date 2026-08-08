import { AnimatePresence, motion } from "framer-motion";
import {
    Bell,
    Check,
    ChevronRight,
    Clock,
    Database,
    FileText,
    Moon,
    Send,
    User,
    Zap
} from "lucide-react";
import React, { useEffect, useState } from "react";

// --- Simulation 1: Stress Test (Chat UI) ---
interface ChatMessageProps {
  text: string;
  isUser: boolean;
  isBijou?: boolean;
  timestamp: string;
}

const ChatMessage: React.FC<ChatMessageProps> = ({
  text,
  isUser,
  isBijou = false,
  timestamp,
}) => (
  <motion.div
    initial={{ opacity: 0, y: 10, scale: 0.95 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
  >
    <div
      className={`max-w-[80%] rounded-lg p-3 relative shadow-sm ${
        isUser
          ? "bg-[#005c4b] text-white rounded-tr-none" // WhatsApp User Green (Dark Mode)
          : isBijou
            ? "bg-[#202c33] text-white rounded-tl-none border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]"
            : "bg-[#202c33] text-white rounded-tl-none border border-white/10" // Generic Bot
      }`}
    >
      <p className="text-sm leading-relaxed">{text}</p>
      <div className="flex justify-end items-center gap-1 mt-1 opacity-70">
        <span className="text-[10px]">{timestamp}</span>
        {isUser && <Check className="w-3 h-3" />}
        {!isUser && isBijou && <Check className="w-3 h-3 text-emerald-400" />}
      </div>

      {/* Triangle tail */}
      <div
        className={`absolute top-0 w-0 h-0 border-[6px] border-transparent ${
          isUser
            ? "right-[-6px] border-t-[#005c4b]"
            : isBijou
              ? "left-[-6px] border-t-[#202c33]"
              : "left-[-6px] border-t-[#202c33]"
        }`}
      />
    </div>
  </motion.div>
);

const StressTestSimulation = () => {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStep((prev) => (prev < 4 ? prev + 1 : 0));
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="grid md:grid-cols-2 gap-6 h-[500px]">
      {/* Generic AI - Fail */}
      <div className="glass-panel rounded-3xl overflow-hidden flex flex-col border border-white/10">
        <div className="bg-[#202c33] p-4 flex items-center gap-3 border-b border-white/5">
          <div className="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center text-white font-bold">
            AI
          </div>
          <div>
            <div className="font-bold text-white text-sm">Generic Bot 🤖</div>
            <div className="text-xs text-gray-400">Online</div>
          </div>
        </div>
        <div className="flex-1 bg-[#0b141a] p-4">
          <AnimatePresence mode="wait">
            {step >= 0 && (
              <ChatMessage
                key="g1"
                text="Walau eh, so expensive ah?"
                isUser={true}
                timestamp="10:42 AM"
              />
            )}
            {step >= 1 && (
              <ChatMessage
                key="g2"
                text="I apologize, I do not understand 'Walau'. Could you please rephrase your query in standard English?"
                isUser={false}
                timestamp="10:42 AM"
              />
            )}
            {step >= 2 && (
              <ChatMessage
                key="g3"
                text="Aiyo... nevermind la."
                isUser={true}
                timestamp="10:43 AM"
              />
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Bijou AI - Pass */}
      <div className="glass-panel-3d rounded-3xl overflow-hidden flex flex-col border border-emerald-500/30 shadow-[0_0_40px_rgba(16,185,129,0.1)]">
        <div className="bg-[#202c33] p-4 flex items-center gap-3 border-b border-emerald-500/20">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold shadow-[0_0_15px_rgba(16,185,129,0.4)]">
              B
            </div>
            <div className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-400 rounded-full border-2 border-[#202c33]"></div>
          </div>
          <div>
            <div className="font-bold text-white text-sm">Bijou Assistant</div>
            <div className="text-xs text-emerald-400 font-medium">
              Typing...
            </div>
          </div>
        </div>
        <div className="flex-1 bg-[#0b141a] p-4">
          <AnimatePresence mode="wait">
            {step >= 0 && (
              <ChatMessage
                key="b1"
                text="Walau eh, so expensive ah?"
                isUser={true}
                timestamp="10:42 AM"
              />
            )}
            {step >= 1 && (
              <ChatMessage
                key="b2"
                text="Aiya boss, interest rate steady one, don't worry. This unit got best view! Value for money. Can set viewing? 😉"
                isUser={false}
                isBijou={true}
                timestamp="10:42 AM"
              />
            )}
            {step >= 2 && (
              <ChatMessage
                key="b3"
                text="Ok can. Tomorrow 2pm?"
                isUser={true}
                timestamp="10:43 AM"
              />
            )}
            {step >= 3 && (
              <ChatMessage
                key="b4"
                text="On! I book the slot for you. See you tomorrow boss! 🤝"
                isUser={false}
                isBijou={true}
                timestamp="10:43 AM"
              />
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

// --- Simulation 2: Speed Run (Timer Comparison) ---
const SpeedRunSimulation = () => {
  const [humanTime, setHumanTime] = useState(0);
  const [bijouTime, setBijouTime] = useState(0);
  const [bijouFinished, setBijouFinished] = useState(false);

  useEffect(() => {
    // Reset
    setHumanTime(0);
    setBijouTime(0);
    setBijouFinished(false);

    const interval = setInterval(() => {
      setHumanTime((prev) => prev + 0.1);
      setBijouTime((prev) => {
        if (prev < 1.4) return prev + 0.1;
        setBijouFinished(true);
        return 1.4;
      });
    }, 100);

    return () => clearInterval(interval);
  }, []); // Simple loop for demo effect

  return (
    <div className="grid md:grid-cols-2 gap-8 items-center h-[500px]">
      {/* Left: Human Agent */}
      <div className="glass-panel p-8 rounded-3xl border border-white/10 h-full flex flex-col relative overflow-hidden opacity-60">
        <div className="absolute top-4 left-4 bg-red-500/20 text-red-400 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border border-red-500/20">
          Human Agent
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-center space-y-6">
          <div className="w-24 h-24 rounded-full border-4 border-white/10 border-t-white animate-spin flex items-center justify-center">
            <User className="w-8 h-8 text-gray-500" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white mb-2">
              Searching Files...
            </h3>
            <p className="text-sm text-gray-500 max-w-[200px] mx-auto">
              "Wait ah, let me find the brochure first..."
            </p>
          </div>
          <div className="text-4xl font-mono font-bold text-gray-400">
            {Math.floor(humanTime * 10)}m {Math.floor((humanTime * 100) % 60)}s
          </div>
        </div>
      </div>

      {/* Right: Bijou */}
      <div className="glass-panel-3d p-8 rounded-3xl border border-emerald-500/30 bg-emerald-900/10 h-full flex flex-col relative overflow-hidden">
        <div className="absolute top-4 left-4 bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border border-emerald-500/20 flex items-center gap-2">
          <Zap className="w-3 h-3 fill-current" />
          Bijou Speed Mode
        </div>

        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="w-full max-w-sm space-y-4 mb-8">
            {/* Step 1 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3 bg-white/5 p-3 rounded-lg border border-white/5"
            >
              <Database className="w-5 h-5 text-emerald-400" />
              <span className="text-sm text-white">
                Querying Knowledge Base
              </span>
              <Check className="w-4 h-4 text-emerald-400 ml-auto" />
            </motion.div>
            {/* Step 2 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{
                opacity: bijouTime > 0.5 ? 1 : 0,
                x: bijouTime > 0.5 ? 0 : -20,
              }}
              className="flex items-center gap-3 bg-white/5 p-3 rounded-lg border border-white/5"
            >
              <FileText className="w-5 h-5 text-blue-400" />
              <span className="text-sm text-white">Brochure.pdf Found</span>
              <Check className="w-4 h-4 text-emerald-400 ml-auto" />
            </motion.div>
            {/* Step 3 */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{
                opacity: bijouTime > 1.0 ? 1 : 0,
                x: bijouTime > 1.0 ? 0 : -20,
              }}
              className="flex items-center gap-3 bg-emerald-500/20 p-3 rounded-lg border border-emerald-500/20"
            >
              <Send className="w-5 h-5 text-emerald-400" />
              <span className="text-sm text-emerald-100 font-bold">
                Sent to WhatsApp
              </span>
              <Check className="w-4 h-4 text-emerald-400 ml-auto" />
            </motion.div>
          </div>

          <div className="text-center">
            <div className="text-xs text-emerald-400 uppercase tracking-widest font-bold mb-2">
              Total Time
            </div>
            <div className="text-6xl font-mono font-black text-white flex items-center justify-center gap-2">
              {bijouTime.toFixed(1)}
              <span className="text-2xl text-gray-400">s</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// --- Simulation 3: Night Dashboard (Analytics) ---
const NightDashboardSimulation = () => {
  const [step, setStep] = useState(0);
  const [leadScore, setLeadScore] = useState(0);
  // 0: Idle (2:41 AM)
  // 1: User: "Hi boss, viewing tmrw?"
  // 2: Bijou: "Got slot 2pm."
  // 3: User: "On."
  // 4: Success (Lead + Calendar)

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      while (mounted) {
        setStep(0);
        setLeadScore(0);
        await new Promise((r) => setTimeout(r, 2000));
        if (!mounted) break;
        setStep(1);
        await new Promise((r) => setTimeout(r, 2000));
        if (!mounted) break;
        setStep(2);
        await new Promise((r) => setTimeout(r, 2500)); // Processing
        if (!mounted) break;
        setStep(3);
        await new Promise((r) => setTimeout(r, 1500));
        if (!mounted) break;

        // Lead score animation
        setStep(4);
        const targetScore = 98;
        const duration = 1000;
        const startTime = Date.now();

        while (Date.now() - startTime < duration) {
          if (!mounted) break;
          const progress = (Date.now() - startTime) / duration;
          setLeadScore(
            Math.min(Math.floor(progress * targetScore), targetScore),
          );
          await new Promise((r) => requestAnimationFrame(r));
        }
        setLeadScore(targetScore);

        await new Promise((r) => setTimeout(r, 6000));
      }
    };
    run();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="grid md:grid-cols-2 gap-6 h-[500px]">
      {/* Left: Phone UI */}
      <div className="glass-panel border-white/10 rounded-3xl p-4 flex flex-col relative overflow-hidden bg-black">
        {/* Header */}
        <div className="flex items-center gap-3 pb-4 border-b border-white/10 z-10 bg-black/50 backdrop-blur-md">
          <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-white text-xs">
            B
          </div>
          <div>
            <div className="text-white text-sm font-bold">Bijou Auto-Sales</div>
            <div className="text-emerald-500 text-[10px]">Online</div>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 py-4 space-y-4">
          {step >= 1 && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-[#202c33] p-3 rounded-lg rounded-tl-none max-w-[85%] border border-white/5"
            >
              <p className="text-xs text-gray-200">
                Hi boss, Honda Civic got promo? Can test drive tomorrow?
              </p>
              <span className="text-[10px] text-gray-500 block text-right mt-1">
                02:42 AM
              </span>
            </motion.div>
          )}

          {step >= 2 && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-[#005c4b] p-3 rounded-lg rounded-tr-none max-w-[85%] ml-auto shadow-lg shadow-emerald-900/20"
            >
              <p className="text-xs text-white">
                Got boss! Merdeka Promo (RM2k rebate + Voucher) ending soon.
                Tomorrow 2pm got slot. I book for you?
              </p>
              <span className="text-[10px] text-emerald-200 block text-right mt-1">
                02:42 AM
              </span>
            </motion.div>
          )}

          {step >= 3 && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-[#202c33] p-3 rounded-lg rounded-tl-none max-w-[85%] border border-white/5"
            >
              <p className="text-xs text-gray-200">On. 2pm set.</p>
              <span className="text-[10px] text-gray-500 block text-right mt-1">
                02:43 AM
              </span>
            </motion.div>
          )}

          {step >= 4 && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-[#005c4b] p-3 rounded-lg rounded-tr-none max-w-[85%] ml-auto"
            >
              <p className="text-xs text-white">
                Cantik! Appointment set. See you boss. 🤝
              </p>
              <span className="text-[10px] text-emerald-200 block text-right mt-1">
                02:43 AM
              </span>
            </motion.div>
          )}
        </div>
      </div>

      {/* Right: Bijou Brain */}
      <div className="glass-panel-3d border-emerald-500/30 rounded-3xl p-6 flex flex-col bg-emerald-900/5 relative overflow-hidden">
        {/* Time & Status */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <div className="text-xs text-emerald-400 font-mono uppercase tracking-widest mb-1">
              System Time
            </div>
            <div className="text-3xl font-mono text-white font-bold flex items-center gap-2">
              02:4{step < 3 ? "2" : "3"}{" "}
              <span className="text-base text-gray-500">AM</span>
            </div>
          </div>
          <div
            className={`px-3 py-1 rounded-full border text-xs font-bold uppercase transition-colors duration-300 ${step === 0 ? "border-gray-600 text-gray-400" : "border-emerald-500 text-emerald-400 animate-pulse bg-emerald-900/20"}`}
          >
            {step === 0 ? "Monitoring" : "Processing"}
          </div>
        </div>

        {/* Action Visuals */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Knowledge Base */}
          <div className="bg-black/40 rounded-xl p-4 border border-white/10 relative overflow-hidden">
            <div className="text-[10px] text-gray-400 uppercase mb-2">
              Knowledge Base
            </div>
            <div className="flex items-center gap-2">
              <Database
                className={`w-5 h-5 transition-colors ${step >= 1 ? "text-blue-400" : "text-gray-600"}`}
              />
              <div className="text-sm font-medium text-white transition-opacity">
                {step === 0 && <span className="opacity-50">Idle</span>}
                {step >= 1 && (
                  <span className="animate-pulse">Voucher: Active</span>
                )}
              </div>
            </div>
            {step === 1 && (
              <motion.div
                layoutId="kb-scan"
                className="absolute bottom-0 left-0 h-1 bg-blue-500 w-full animate-progress"
              />
            )}
          </div>

          {/* Calendar */}
          <div className="bg-black/40 rounded-xl p-4 border border-white/10 relative overflow-hidden">
            <div className="text-[10px] text-gray-400 uppercase mb-2">
              Calendar API
            </div>
            <div className="flex items-center gap-2">
              <Clock
                className={`w-5 h-5 transition-colors ${step >= 2 ? "text-emerald-400" : "text-gray-600"}`}
              />
              <div className="text-sm font-medium text-white">
                {step < 2 && <span className="opacity-50">Idle</span>}
                {step >= 2 && "Slot Found: 2pm"}
              </div>
            </div>
            {step >= 4 && (
              <motion.div
                layoutId="highlight"
                className="absolute inset-0 bg-emerald-500/10 border-2 border-emerald-500 rounded-xl"
              />
            )}
          </div>
        </div>

        {/* Lead Score Large */}
        <div className="flex-1 flex items-center justify-center relative">
          <div className="relative w-40 h-40">
            <svg className="w-full h-full -rotate-90">
              <circle
                cx="50%"
                cy="50%"
                r="45"
                stroke="#1f2937"
                strokeWidth="6"
                fill="transparent"
              />
              <motion.circle
                cx="50%"
                cy="50%"
                r="45"
                stroke="#10b981"
                strokeWidth="6"
                fill="transparent"
                strokeDasharray={2 * Math.PI * 45}
                strokeDashoffset={
                  2 * Math.PI * 45 - (leadScore / 100) * (2 * Math.PI * 45)
                }
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="text-xs text-gray-500 uppercase font-bold">
                Lead Score
              </div>
              <div className="text-5xl font-bold text-white font-mono">
                {leadScore}
              </div>
            </div>
          </div>
        </div>

        {/* Notification Pop */}
        <AnimatePresence>
          {step >= 4 && (
            <motion.div
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 50, opacity: 0 }}
              className="absolute bottom-4 left-4 right-4 bg-emerald-600 text-white p-3 rounded-xl shadow-lg flex items-center gap-3 border border-emerald-400/30"
            >
              <div className="bg-white/20 p-2 rounded-lg">
                <Bell className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-bold opacity-80">
                  NEW LEAD CAPTURED
                </div>
                <div className="text-sm font-bold">Added to Calendar</div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

interface ViralPillarsProps {
  onOpenModal: () => void;
}

export const ViralPillars: React.FC<ViralPillarsProps> = ({ onOpenModal }) => {
  const [activeTab, setActiveTab] = useState<"stress" | "speed" | "dashboard">(
    "stress",
  );

  return (
    <section className="py-24 bg-dark-900/50 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/80 pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-6">
            Why Bijou Goes{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
              Viral
            </span>
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto text-lg">
            The difference is in the details. See how we outperform generic AI
            and human agents.
          </p>
        </div>

        <div className="flex justify-center mb-12">
          <div className="bg-black/40 p-1.5 rounded-2xl flex flex-wrap justify-center gap-2 border border-white/10 backdrop-blur-md">
            {["stress", "speed", "dashboard"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab as any)}
                className={`px-6 py-3 rounded-xl text-sm font-bold transition-all duration-300 flex items-center gap-2 relative overflow-hidden group ${
                  activeTab === tab
                    ? "bg-emerald-500 text-dark-900 shadow-[0_0_20px_rgba(16,185,129,0.3)]"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                } ${
                  tab === "dashboard" && activeTab !== "dashboard"
                    ? "border border-emerald-500/30 text-emerald-400/90 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                    : ""
                }`}
              >
                {/* Special glow for dashboard button when inactive to tempt user */}
                {tab === "dashboard" && activeTab !== "dashboard" && (
                  <span className="absolute inset-0 bg-emerald-500/5 animate-pulse"></span>
                )}

                {tab === "stress" && (
                  <>
                    <User className="w-4 h-4" /> The Stress Test
                  </>
                )}
                {tab === "speed" && (
                  <>
                    <Clock className="w-4 h-4" /> Speed Run
                  </>
                )}
                {tab === "dashboard" && (
                  <>
                    <Moon className="w-4 h-4" /> Money While You Sleep
                  </>
                )}
              </button>
            ))}
          </div>
        </div>

        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -15 }}
          transition={{ duration: 0.4 }}
          className="max-w-5xl mx-auto"
        >
          {activeTab === "stress" && <StressTestSimulation />}
          {activeTab === "speed" && <SpeedRunSimulation />}
          {activeTab === "dashboard" && <NightDashboardSimulation />}
        </motion.div>

        <div className="mt-12 text-center">
          <button
            onClick={onOpenModal}
            className="bg-emerald-500 hover:bg-emerald-400 text-dark-900 font-bold py-4 px-8 rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all flex items-center gap-2 mx-auto group"
          >
            Try Bijou Free for 14 Days
            <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </section>
  );
};
