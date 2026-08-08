import type React from "react";
import { motion } from "framer-motion";

export const StoryLunchRushClinic: React.FC = () => {
  const messages = [
    {
      sender: "customer",
      time: "12:14 PM",
      text: "My daughter tooth pain since morning, very bad. Can see doctor today?",
    },
    {
      sender: "bijou",
      time: "12:14 PM",
      text: "Adoi, tooth pain since morning — mesti sakit sangat. Let me check slots now. Is it the upper or lower tooth? And any swelling on the face?",
    },
    {
      sender: "customer",
      time: "12:15 PM",
      text: "Lower right, no swelling. She 8 years old.",
    },
    {
      sender: "bijou",
      time: "12:15 PM",
      text: "OK — for kids tooth pain without swelling, Dr Lim can see her at 2:30pm today. I book now and send you the address. Please give her panadol first to help with the pain.",
    },
    {
      sender: "customer",
      time: "12:16 PM",
      text: "Thank you so much! Very helpful",
    },
  ];

  return (
    <section className="py-20 relative overflow-hidden bg-dark-900/50">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/3 w-[500px] h-[500px] bg-blue-900/10 rounded-full blur-[140px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[300px] h-[300px] bg-[#D4AF37]/5 rounded-full blur-[100px]" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left: WhatsApp mock */}
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5 }}
            className="relative order-2 md:order-1"
          >
            {/* Phone frame */}
            <div className="glass-panel-3d rounded-3xl border border-white/10 overflow-hidden max-w-sm mx-auto">
              {/* Chat header */}
              <div className="bg-[#0d2040] px-4 py-3 flex items-center gap-3 border-b border-white/10">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-400 to-cyan-500 flex items-center justify-center text-white text-sm font-black">
                  B
                </div>
                <div>
                  <div className="text-white text-sm font-bold">
                    Bijou — Klinik Gigi
                  </div>
                  <div className="text-blue-400 text-xs flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
                    Active now · 12:14 PM
                  </div>
                </div>
              </div>

              {/* Lunch rush banner */}
              <div className="bg-amber-500/10 border-b border-amber-500/20 px-3 py-1.5 text-center">
                <p className="text-amber-400 text-[10px] font-bold uppercase tracking-wider">
                  Lunch Rush — 12-2pm — Staff on break
                </p>
              </div>

              {/* Messages */}
              <div className="bg-[#080f1f] px-3 py-4 space-y-3 min-h-[320px]">
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.12 }}
                    className={`flex ${msg.sender === "customer" ? "justify-start" : "justify-end"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-3 py-2 text-xs leading-relaxed ${
                        msg.sender === "customer"
                          ? "bg-white/10 text-gray-200 rounded-tl-sm"
                          : "bg-[#0d2040] border border-blue-500/20 text-blue-100 rounded-tr-sm"
                      }`}
                    >
                      <p>{msg.text}</p>
                      <p
                        className={`text-[10px] mt-1 ${msg.sender === "customer" ? "text-gray-500" : "text-blue-500/60"}`}
                      >
                        {msg.time}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Footer */}
              <div className="bg-blue-900/30 px-3 py-2 text-center">
                <p className="text-blue-400 text-xs font-bold">
                  2:30pm booked. Staff still on lunch break.
                </p>
              </div>
            </div>
          </motion.div>

          {/* Right: Copy */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="space-y-6 order-1 md:order-2"
          >
            <div className="inline-block px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-bold uppercase tracking-wider">
              Healthcare Vertical — Real Scenario
            </div>

            <h2 className="text-3xl md:text-4xl font-black text-white leading-tight">
              The Lunch Rush Clinic.{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
                Triaged. Booked. Done.
              </span>
            </h2>

            <p className="text-gray-400 text-lg leading-relaxed">
              12pm to 2pm — your staff eat. Your WhatsApp doesn't.
            </p>

            <p className="text-gray-400 leading-relaxed">
              Bijou asked the right clinical questions, flagged urgency (child,
              tooth pain since morning), skipped swelling screening, and booked
              the next available slot. The parent didn't call seven other
              clinics. She came to yours.
            </p>

            {/* MS translation */}
            <div className="border-l-2 border-blue-400/30 pl-4">
              <p className="text-gray-500 text-sm italic">
                "Masa rehat tengah hari pun Bijou boleh triage dan buat
                appointment. Pesakit tak perlu tunggu."
              </p>
              <p className="text-gray-600 text-xs mt-1">
                — Even during lunch break, Bijou can triage and make
                appointments. Patients don't need to wait.
              </p>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <span className="px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
                Smart triage
              </span>
              <span className="px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
                Cal.com booking
              </span>
              <span className="px-3 py-1.5 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/20 text-[#D4AF37] text-xs font-semibold">
                24/7 coverage
              </span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
