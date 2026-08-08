import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Building2, Gamepad2, Coffee, Stethoscope, ArrowRight, CheckCircle2, Loader2 } from 'lucide-react';

const playbooks = [
    {
        id: 'property',
        label: 'Property',
        icon: <Building2 className="w-5 h-5" />,
        color: 'blue',
        title: 'The "Viewing Machine" Playbook',
        description: 'Agents waste 70% of time filtering window shoppers. Bijou qualifies budget, location, and urgency before you ever speak to them.',
        stats: ['Auto-sends Brochures', 'Qualifies Budget & Loans', 'Syncs to Google Calendar'],
        chat: {
            user: "Hi, interested in the Mont Kiara unit. Available?",
            bijou: "Hi Boss! Unit still available. Rental RM3.5k. You looking for own stay or investment? 🏙️"
        }
    },
    {
        id: 'dental',
        label: 'Dental',
        icon: <Stethoscope className="w-5 h-5" />,
        color: 'emerald',
        title: 'The "No More No-Show" Playbook',
        description: 'Empty chairs cost money. Bijou sends reminders, handles rescheduling, and even detects emergency keywords like "pain" to prioritize booking.',
        stats: ['Emergency Triage', 'Deposit Collection Links', 'Post-Treatment Checkups'],
        chat: {
            user: "My tooth pain since last night. Got slot today?",
            bijou: "Aiya sorry to hear! Emergency slot got 2pm. I book for you now? Can ease pain fast. 🦷"
        }
    },
    {
        id: 'gaming',
        label: 'Gaming',
        icon: <Gamepad2 className="w-5 h-5" />,
        color: 'purple',
        title: 'The "Tournament Host" Playbook',
        description: 'Managing registration for 100+ teams on WhatsApp is a nightmare. Bijou automates team registration, payment verification, and bracket updates.',
        stats: ['Team Data Collection', 'Payment Receipt OCR', 'Automated FAQs'],
        chat: {
            user: "Nak register team Valorant tourney.",
            bijou: "On boss! Send me Team Name and Captain IC. Registration fee RM50 transfer here... 🎮"
        }
    },
    {
        id: 'fnb',
        label: 'F&B',
        icon: <Coffee className="w-5 h-5" />,
        color: 'orange',
        title: 'The "Peak Hour" Playbook',
        description: 'Don\'t let staff answer phones during dinner rush. Bijou handles reservations and menu questions so your team can focus on serving food.',
        stats: ['Table Reservation', 'Menu Recommendations', 'Dietary Restriction Check'],
        chat: {
            user: "Table for 5 tonight 8pm?",
            bijou: "Checking boss... Alamak 8pm full. 8:30pm can? We reserve nice corner table for you. 🍔"
        }
    }
];

interface PlaybooksProps {
  onOpenModal: () => void;
}

export const Playbooks: React.FC<PlaybooksProps> = ({ onOpenModal }) => {
  const [activeTab, setActiveTab] = useState<(typeof playbooks)[number]>(playbooks[0]!);
  const [chatStage, setChatStage] = useState<'hidden' | 'user' | 'typing' | 'bijou'>('hidden');

  // Reset and play animation sequence when tab changes
  useEffect(() => {
    setChatStage('hidden');
    
    // Sequence timelines
    const t1 = setTimeout(() => setChatStage('user'), 200);
    const t2 = setTimeout(() => setChatStage('typing'), 1000);
    const t3 = setTimeout(() => setChatStage('bijou'), 2500);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [activeTab]);

  return (
    <section className="py-24 relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
                <h2 className="text-3xl md:text-5xl font-bold mb-4">Vertical Playbooks</h2>
                <p className="text-gray-400">Pre-trained conversation flows for your specific industry.</p>
            </div>

            <div className="flex flex-wrap justify-center gap-4 mb-12">
                {playbooks.map((pb) => (
                    <button
                        key={pb.id}
                        onClick={() => setActiveTab(pb)}
                        className={`flex items-center gap-2 px-6 py-3 rounded-full border transition-all duration-300 font-medium ${
                            activeTab.id === pb.id 
                            ? `bg-${pb.color}-500/10 border-${pb.color}-500 text-${pb.color}-400 shadow-[0_0_15px_rgba(0,0,0,0.5)]` 
                            : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                        }`}
                    >
                        {pb.icon}
                        {pb.label}
                    </button>
                ))}
            </div>

            <div className="grid lg:grid-cols-2 gap-12 items-center">
                {/* Content Side */}
                <motion.div
                    key={activeTab.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4 }}
                    className="space-y-8"
                >
                    <div>
                        <h3 className={`text-3xl font-bold text-white mb-4`}>{activeTab.title}</h3>
                        <p className="text-gray-400 text-lg leading-relaxed">{activeTab.description}</p>
                    </div>

                    <div className="space-y-3">
                        {activeTab.stats.map((stat, i) => (
                            <div key={i} className="flex items-center gap-3">
                                <CheckCircle2 className={`w-5 h-5 text-${activeTab.color}-400`} />
                                <span className="text-gray-300">{stat}</span>
                            </div>
                        ))}
                    </div>

                    <button 
                        onClick={onOpenModal}
                        className={`flex items-center gap-2 text-${activeTab.color}-400 font-bold hover:gap-3 transition-all`}
                    >
                        View {activeTab.label} Demo <ArrowRight className="w-4 h-4" />
                    </button>
                </motion.div>

                {/* Chat Preview Side */}
                <div className="relative h-[400px]">
                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/20 to-blue-500/20 blur-[60px] rounded-full" />
                    <div className="glass-panel-3d p-6 rounded-3xl border border-white/10 relative bg-black/40 h-full flex flex-col">
                        
                        {/* Status Bar Mockup */}
                        <div className="flex items-center gap-3 border-b border-white/5 pb-4 mb-4">
                           <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center font-bold text-dark-900 text-xs">B</div>
                           <div>
                              <div className="text-xs font-bold text-white">Bijou Assistant</div>
                              <div className="text-[10px] text-emerald-400 flex items-center gap-1">
                                 <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"/> Online
                              </div>
                           </div>
                        </div>

                        <div className="space-y-4 flex-1 overflow-hidden">
                           <AnimatePresence mode='popLayout'>
                                {/* User Msg */}
                                {chatStage !== 'hidden' && (
                                    <motion.div
                                        key="user"
                                        initial={{ opacity: 0, y: 20, scale: 0.9 }}
                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                        className="flex justify-end"
                                    >
                                        <div className={`bg-${activeTab.color}-800/80 backdrop-blur-md text-white p-4 rounded-2xl rounded-tr-none max-w-[85%] shadow-lg border border-white/5`}>
                                            <p className="text-sm">{activeTab.chat.user}</p>
                                        </div>
                                    </motion.div>
                                )}

                                {/* Typing Indicator */}
                                {chatStage === 'typing' && (
                                    <motion.div
                                        key="typing"
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.9 }}
                                        className="flex justify-start"
                                    >
                                        <div className="bg-white/10 text-white p-4 rounded-2xl rounded-tl-none border border-white/5 flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}/>
                                            <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}/>
                                            <span className="w-1.5 h-1.5 bg-white/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}/>
                                        </div>
                                    </motion.div>
                                )}

                                {/* Bijou Msg */}
                                {chatStage === 'bijou' && (
                                    <motion.div
                                        key="bijou"
                                        initial={{ opacity: 0, y: 20, scale: 0.9 }}
                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                        className="flex justify-start"
                                    >
                                        <div className="flex gap-3 max-w-[90%]">
                                            <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center font-bold text-dark-900 text-xs mt-auto flex-shrink-0 shadow-[0_0_10px_rgba(16,185,129,0.5)]">B</div>
                                            <div className="bg-white/10 text-white p-4 rounded-2xl rounded-tl-none border border-white/5 backdrop-blur-md">
                                                <p className="text-sm">{activeTab.chat.bijou}</p>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                           </AnimatePresence>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
  );
};