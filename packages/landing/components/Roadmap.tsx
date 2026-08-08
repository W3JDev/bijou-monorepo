import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Rocket, Languages, Mic, Globe, Check } from 'lucide-react';

const phases = [
  {
    phase: "Phase 5",
    title: "Ad Integrations",
    icon: <Rocket className="w-6 h-6" />,
    desc: "Direct integration with Facebook & TikTok Lead Forms to intercept leads instantly.",
    color: "blue"
  },
  {
    phase: "Phase 6",
    title: "Mobile App",
    icon: <Globe className="w-6 h-6" />,
    desc: "iOS/Android dashboard for business owners to monitor Bijou's performance on the go.",
    color: "emerald"
  },
  {
    phase: "Phase 7",
    title: "Voice AI",
    icon: <Mic className="w-6 h-6" />,
    desc: "Bijou learns to speak. Handle phone calls with the same Manglish personality.",
    color: "purple"
  },
  {
    phase: "Phase 8",
    title: "ASEAN Expansion",
    icon: <Languages className="w-6 h-6" />,
    desc: "Support for Bahasa Indonesia, Tagalog, and Thai mixed dialects.",
    color: "orange"
  }
];

const languages = [
  { id: 'ms', label: 'Bahasa Melayu (Formal)' },
  { id: 'zh', label: 'Mandarin Mix' },
  { id: 'ta', label: 'Tamil Mix' }
];

export const Roadmap: React.FC = () => {
  const [votes, setVotes] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const storedVotes = localStorage.getItem('bijou_language_votes');
    if (storedVotes) {
      setVotes(JSON.parse(storedVotes));
    }
  }, []);

  const handleVote = (id: string) => {
    const newVotes = { ...votes, [id]: !votes[id] };
    setVotes(newVotes);
    localStorage.setItem('bijou_language_votes', JSON.stringify(newVotes));
  };

  return (
    <section id="roadmap" className="py-24 relative overflow-hidden bg-dark-800/50">
       <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[120px] pointer-events-none" />
       
       <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center mb-20">
             <div className="inline-block px-3 py-1 mb-4 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-bold uppercase tracking-wider">
                Future Vision
             </div>
             <h2 className="text-3xl md:text-5xl font-bold mb-6">Product Roadmap</h2>
             <p className="text-gray-400 max-w-2xl mx-auto">
                We are building the future of Southeast Asian commerce automation.
             </p>
          </div>

          {/* Timeline Grid */}
          <div className="grid md:grid-cols-4 gap-8 relative">
             {/* Connector Line */}
             <div className="hidden md:block absolute top-8 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-900 via-emerald-900 to-orange-900 z-0" />
             
             {phases.map((item, idx) => (
                <motion.div
                   key={idx}
                   initial={{ opacity: 0, y: 30 }}
                   whileInView={{ opacity: 1, y: 0 }}
                   viewport={{ once: true }}
                   transition={{ delay: idx * 0.2 }}
                   className="relative z-10 group"
                >
                   {/* Node Dot */}
                   <div className={`w-16 h-16 mx-auto mb-6 rounded-2xl glass-panel-3d flex items-center justify-center text-${item.color}-400 border border-${item.color}-500/30 shadow-[0_0_20px_rgba(0,0,0,0.3)] group-hover:scale-110 transition-transform duration-300 relative bg-dark-900`}>
                      {item.icon}
                      <div className={`absolute -bottom-2 -right-2 w-4 h-4 rounded-full bg-${item.color}-500 border-2 border-dark-900`} />
                   </div>

                   <div className="text-center">
                      <div className={`text-xs font-bold text-${item.color}-500 uppercase tracking-widest mb-2`}>{item.phase}</div>
                      <h3 className="text-xl font-bold text-white mb-3">{item.title}</h3>
                      <p className="text-gray-400 text-sm leading-relaxed">{item.desc}</p>
                   </div>
                </motion.div>
             ))}
          </div>

          {/* Language Support Callout */}
          <div className="mt-24 glass-panel-3d p-8 rounded-3xl border border-white/10 relative overflow-hidden">
             <div className="absolute inset-0 bg-gradient-to-r from-emerald-900/20 to-blue-900/20" />
             <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
                <div>
                   <h3 className="text-2xl font-bold text-white mb-2">More than just Manglish?</h3>
                   <p className="text-gray-400">We are currently training models for other dialects. Vote for what you need next.</p>
                </div>
                <div className="flex gap-4 flex-wrap justify-center">
                   {languages.map((lang) => (
                     <button
                       key={lang.id}
                       onClick={() => handleVote(lang.id)}
                       className={`px-4 py-2 rounded-full border text-sm transition-all flex items-center gap-2 ${
                         votes[lang.id]
                           ? 'bg-emerald-500 text-dark-900 border-emerald-400 font-bold shadow-[0_0_15px_rgba(16,185,129,0.3)]'
                           : 'bg-white/5 border-white/10 text-gray-300 hover:bg-white/10'
                       }`}
                     >
                       {lang.label}
                       {votes[lang.id] && <Check className="w-3 h-3" />}
                     </button>
                   ))}
                </div>
             </div>
          </div>
       </div>
    </section>
  );
};
