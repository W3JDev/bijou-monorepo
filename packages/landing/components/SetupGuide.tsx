import React from 'react';
import { motion } from 'framer-motion';
import { QrCode, FileText, Rocket } from 'lucide-react';

const steps = [
    {
        icon: <QrCode className="w-8 h-8" />,
        title: "1. Scan & Connect",
        desc: "Scan the QR code with your business WhatsApp. No API application required."
    },
    {
        icon: <FileText className="w-8 h-8" />,
        title: "2. Upload Knowledge",
        desc: "Upload your PDF price list, website URL, or paste your FAQs. Bijou learns in seconds."
    },
    {
        icon: <Rocket className="w-8 h-8" />,
        title: "3. Go Live",
        desc: "Bijou starts intercepting new chats immediately. You can take over manually anytime."
    }
];

export const SetupGuide: React.FC = () => {
  return (
    <section className="py-24 border-t border-white/5 bg-black">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
                <div className="inline-block px-3 py-1 mb-4 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-bold uppercase tracking-wider">
                    Zero Technical Skills Needed
                </div>
                <h2 className="text-3xl md:text-5xl font-bold mb-4">5 Minutes to Automation</h2>
                <p className="text-gray-400">If you can forward a WhatsApp message, you can set up Bijou.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 relative">
                 {/* Connector Line */}
                 <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-0.5 bg-gradient-to-r from-blue-500/20 via-emerald-500/20 to-purple-500/20 border-t border-white/10 border-dashed" />

                {steps.map((step, idx) => (
                    <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: idx * 0.2 }}
                        className="relative z-10 flex flex-col items-center text-center"
                    >
                        <div className="w-24 h-24 rounded-2xl glass-panel-3d flex items-center justify-center text-emerald-400 mb-6 shadow-lg shadow-emerald-900/20 border border-white/10 bg-dark-900">
                            {step.icon}
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">{step.title}</h3>
                        <p className="text-sm text-gray-500 max-w-[250px]">{step.desc}</p>
                    </motion.div>
                ))}
            </div>
        </div>
    </section>
  );
};
