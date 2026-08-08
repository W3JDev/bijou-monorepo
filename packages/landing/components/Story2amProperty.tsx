import type React from "react";
import { motion } from "framer-motion";

export const Story2amProperty: React.FC = () => {
  const messages = [
    {
      sender: "customer",
      time: "2:47 AM",
      text: "Hi boss, can view property? Mont Kiara area, got high floor one?",
    },
    {
      sender: "bijou",
      time: "2:47 AM",
      text: "Wah 3am you still looking — serious buyer lah! Got few units at MK, high floor with balcony. Which date you free to view? I check availability now.",
    },
    {
      sender: "customer",
      time: "2:49 AM",
      text: "Saturday morning can? Budget around 900k",
    },
    {
      sender: "bijou",
      time: "2:49 AM",
      text: "Saturday 10am confirmed. I book for you now and send reminder Friday night. Budget 900k — I shortlist 3 units tonight, you check tomorrow morning. Deal?",
    },
    {
      sender: "customer",
      time: "2:50 AM",
      text: "Wah fast fast. Ok deal!",
    },
  ];

  return (
    <section className="py-20 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 right-1/4 w-[400px] h-[400px] bg-[#0d3d3d]/40 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 left-1/4 w-[300px] h-[300px] bg-[#D4AF37]/5 rounded-full blur-[100px]" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left: Copy */}
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            <div className="inline-block px-3 py-1 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/30 text-[#D4AF37] text-xs font-bold uppercase tracking-wider">
              Property Vertical — Real Scenario
            </div>

            <h2 className="text-3xl md:text-4xl font-black text-white leading-tight">
              The 2am Viewing Inquiry.{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#D4AF37] to-yellow-300">
                Closed by morning.
              </span>
            </h2>

            <p className="text-gray-400 text-lg leading-relaxed">
              Your agent is asleep. Your competitor's is too.{" "}
              <strong className="text-white">Bijou isn't.</strong>
            </p>

            <p className="text-gray-400 leading-relaxed">
              That Saturday booking just happened at 2:47am. No human involved.
              Bijou qualified the budget, shortlisted units, and locked the
              slot — in Manglish, like a colleague, not a bot.
            </p>

            {/* MS translation */}
            <div className="border-l-2 border-[#D4AF37]/30 pl-4">
              <p className="text-gray-500 text-sm italic">
                "Jumaat malam dia tanya. Sabtu pagi dia dah datang viewing.
                Bijou yang uruskan semuanya."
              </p>
              <p className="text-gray-600 text-xs mt-1">
                — Friday night he asked. Saturday morning he came for viewing.
                Bijou handled everything.
              </p>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <span className="px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
                No WABA needed
              </span>
              <span className="px-3 py-1.5 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/20 text-[#D4AF37] text-xs font-semibold">
                Manglish native
              </span>
              <span className="px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
                Cal.com booking
              </span>
            </div>
          </motion.div>

          {/* Right: WhatsApp mock */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="relative"
          >
            {/* Phone frame */}
            <div className="glass-panel-3d rounded-3xl border border-white/10 overflow-hidden max-w-sm mx-auto">
              {/* Chat header */}
              <div className="bg-[#0d3d3d] px-4 py-3 flex items-center gap-3 border-b border-white/10">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-white text-sm font-black">
                  B
                </div>
                <div>
                  <div className="text-white text-sm font-bold">
                    Bijou Assistant
                  </div>
                  <div className="text-emerald-400 text-xs flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                    Active now · 2:47 AM
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="bg-[#0a1a10] px-3 py-4 space-y-3 min-h-[320px]">
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
                          : "bg-[#0d3d3d] border border-emerald-500/20 text-emerald-100 rounded-tr-sm"
                      }`}
                    >
                      <p>{msg.text}</p>
                      <p
                        className={`text-[10px] mt-1 ${msg.sender === "customer" ? "text-gray-500" : "text-emerald-500/60"}`}
                      >
                        {msg.time}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Footer */}
              <div className="bg-[#0d3d3d]/80 px-3 py-2 text-center">
                <p className="text-[#D4AF37] text-xs font-bold">
                  Saturday booking confirmed. No human needed.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
