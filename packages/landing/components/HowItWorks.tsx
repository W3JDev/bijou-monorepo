import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Ear, Heart, BrainCircuit, Handshake, ArrowRight } from 'lucide-react';

const steps = [
  {
    icon: <Ear className="w-8 h-8 text-blue-400" />,
    title: "1. Detection Agent",
    subTitle: "Active Listening",
    traceElement: "Input Analysis",
    detail: "Detects frustration, urgency, and slang (Manglish). Identification of intent <100ms.",
    meta: "Status: Listening",
    textColor: "text-blue-400",
    borderColor: "group-hover:border-blue-500/30",
    badgeBorder: "border-blue-500/30",
    badgeText: "text-blue-400",
    dotColor: "bg-blue-500"
  },
  {
    icon: <Heart className="w-8 h-8 text-pink-400" />,
    title: "2. Empathy Agent",
    subTitle: "Tone Shifting",
    traceElement: "EQ Layer",
    detail: "Mirrors user's emotion. If user is angry, tone softens. If user is casual, tone matches.",
    meta: "Status: Adapting",
    textColor: "text-pink-400",
    borderColor: "group-hover:border-pink-500/30",
    badgeBorder: "border-pink-500/30",
    badgeText: "text-pink-400",
    dotColor: "bg-pink-500"
  },
  {
    icon: <BrainCircuit className="w-8 h-8 text-emerald-400" />,
    title: "3. Logic Agent",
    subTitle: "Contextual Response",
    traceElement: "Knowledge Retrieval",
    detail: "Queries business calendar, inventory, or pricing list to formulate the perfect answer.",
    meta: "Status: Thinking",
    textColor: "text-emerald-400",
    borderColor: "group-hover:border-emerald-500/30",
    badgeBorder: "border-emerald-500/30",
    badgeText: "text-emerald-400",
    dotColor: "bg-emerald-500"
  },
  {
    icon: <Handshake className="w-8 h-8 text-purple-400" />,
    title: "4. Closing Agent",
    subTitle: "Conversion",
    traceElement: "Goal Completion",
    detail: "Drives the specific business goal: Booking, Sale, or Lead Capture.",
    meta: "Status: Closing",
    textColor: "text-purple-400",
    borderColor: "group-hover:border-purple-500/30",
    badgeBorder: "border-purple-500/30",
    badgeText: "text-purple-400",
    dotColor: "bg-purple-500"
  }
];

interface HowItWorksProps {
  onOpenModal: () => void;
}

export const HowItWorks: React.FC<HowItWorksProps> = ({ onOpenModal }) => {
  useEffect(() => {
    // Dev-only TRACE simulation. Skipped in production builds to keep
    // browser console clean. (See audit-report.md finding #29.)
    if (!import.meta.env.DEV) return;

    console.group('TRACE System Initiation - Bijou AI');
    console.log('[TenantRouter] Incoming message from +6012-345-6789. TenantID: MY_PROP_01.');

    setTimeout(() => {
        console.log('[EQ Layer] Sentiment Detected: Frustrated (0.75). Intent: Urgent Inquiry.');
        console.log('[EQ Layer] Tone Adjustment: Shifting to "Empathetic + Professional".');
    }, 500);

    setTimeout(() => {
        console.log('[Knowledge Retrieval] Searching vectors for "condo rental near klcc"...');
        console.log('[Knowledge Retrieval] Found 3 matches. Top confidence: 0.92.');
    }, 1000);

    setTimeout(() => {
        console.log('[Goal Completion] Action: Send Brochure PDF.');
        console.log('[Goal Completion] Status: Success. Latency: 45ms.');
        console.groupEnd();
    }, 1500);

  }, []);

  return (
    <section className="py-24 relative overflow-hidden border-t border-white/5">
      {/* Background Elements */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-emerald-900/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center mb-16">
          <div className="inline-block px-3 py-1 mb-4 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-wider">
            Technical Innovation
          </div>
          <h2 className="text-3xl md:text-5xl font-bold mb-4">How Bijou Actually Works</h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            One fast LLM (Gemini 2.5 Flash) with smart context, your knowledge base, and an automatic handover when complexity exceeds threshold. No fake pipeline — just a clear path from message to action.
          </p>
        </div>

        <div className="grid md:grid-cols-4 gap-6 relative">
          {/* Connecting Line (Desktop) */}
          <div className="hidden md:block absolute top-16 left-[12%] right-[12%] h-0.5 bg-gradient-to-r from-blue-500/20 via-emerald-500/50 to-purple-500/20 z-0" />

          {steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.2 }}
              className="relative z-10"
            >
              <div className="flex flex-col items-center text-center group h-full">
                {/* Icon Circle */}
                <div className={`w-32 h-32 rounded-full glass-panel flex flex-col items-center justify-center mb-8 relative group-hover:bg-white/5 transition-all shadow-[0_0_30px_rgba(0,0,0,0.2)] group-hover:shadow-[0_0_40px_rgba(16,185,129,0.15)] border-2 border-transparent ${step.borderColor}`}>
                  {step.icon}
                  <div className={`absolute -bottom-3 px-3 py-1 rounded-full bg-dark-900 border ${step.badgeBorder} text-[10px] font-bold uppercase tracking-wider ${step.badgeText} shadow-lg whitespace-nowrap`}>
                    {step.traceElement}
                  </div>
                </div>
                
                {/* Content Card */}
                <div className="glass-panel-3d p-6 rounded-2xl w-full flex-1 flex flex-col items-center border border-white/5 group-hover:border-emerald-500/20 transition-colors">
                    <h3 className="text-lg font-bold text-white mb-1">{step.title}</h3>
                    <p className={`text-xs font-bold ${step.textColor} mb-4 uppercase tracking-wide opacity-80`}>{step.subTitle}</p>
                    
                    <p className="text-sm text-gray-400 leading-relaxed mb-4">
                       {step.detail}
                    </p>

                    <div className="mt-auto pt-2 flex items-center gap-2 text-xs font-mono text-gray-500">
                        <div className={`w-1.5 h-1.5 rounded-full ${step.dotColor} animate-pulse`} />
                        {step.meta}
                    </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};