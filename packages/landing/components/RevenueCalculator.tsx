import React, { useState } from "react";

interface RevenueCalculatorProps {
  onOpenModal: () => void;
}

export const RevenueCalculator: React.FC<RevenueCalculatorProps> = ({
  onOpenModal,
}) => {
  const [inquiries, setInquiries] = useState(50);
  const [commission, setCommission] = useState(1000);
  const [missedRate, setMissedRate] = useState(50); // percentage

  const annualLoss = Math.floor(
    inquiries * (missedRate / 100) * commission * 12,
  );
  const bijouCost = 299 * 12; // RM299/month PRO plan
  const roi = Math.floor(((annualLoss - bijouCost) / bijouCost) * 100);

  return (
    <section id="revenue" className="py-24 relative bg-dark-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          <div className="space-y-6">
            <div className="inline-block px-3 py-1 rounded-full bg-gold-500/10 border border-gold-400/20 text-gold-400 text-xs font-bold uppercase tracking-wider">
              ROI Calculator
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-white">
              See How Much You're <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-orange-500">
                Leaving on the Table
              </span>
            </h2>
            <p className="text-gray-400 text-lg">
              Human agents miss calls. They sleep. They eat. They have bad days.
              Input your numbers to see what that creates in lost opportunity
              cost versus Bijou.
            </p>

            <div className="space-y-8 pt-6">
              {/* Slider 1 */}
              <div>
                <div className="flex justify-between text-sm font-medium mb-2">
                  <span className="text-gray-300">
                    Monthly Inquiries (WhatsApp/PMs)
                  </span>
                  <span className="text-gold-400 font-bold">{inquiries}</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="500"
                  value={inquiries}
                  onChange={(e) => setInquiries(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-gold-400"
                />
              </div>

              {/* Slider 2 */}
              <div>
                <div className="flex justify-between text-sm font-medium mb-2">
                  <span className="text-gray-300">
                    Avg. Commission / Order Value (RM)
                  </span>
                  <span className="text-gold-400 font-bold">
                    RM {commission}
                  </span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="5000"
                  step="50"
                  value={commission}
                  onChange={(e) => setCommission(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-gold-400"
                />
              </div>

              {/* Slider 3 */}
              <div>
                <div className="flex justify-between text-sm font-medium mb-2">
                  <span className="text-gray-300">
                    Missed Call/Reply Rate (%)
                  </span>
                  <span className="text-red-400 font-bold">{missedRate}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="90"
                  value={missedRate}
                  onChange={(e) => setMissedRate(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  *Industry avg for SMEs is ~48%
                </p>
              </div>
            </div>
          </div>

          <div className="relative">
            <div className="absolute inset-0 bg-gold-500/20 blur-[100px] rounded-full"></div>
            <div className="glass-panel-3d rounded-3xl p-8 border border-white/10 relative text-center">
              <div className="mb-6">
                <div className="text-gray-400 text-sm font-medium uppercase tracking-widest mb-2">
                  Potential Annual Revenue Loss
                </div>
                <div className="text-5xl md:text-6xl font-black text-white text-glow-strong">
                  RM {annualLoss.toLocaleString()}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                  <div className="text-xs text-gray-400 mb-1">
                    Cost of Bijou/Year
                  </div>
                  <div className="text-xl font-bold text-gold-400">
                    RM {bijouCost.toLocaleString()}
                  </div>
                </div>
                <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                  <div className="text-xs text-gray-400 mb-1">
                    Potential ROI
                  </div>
                  <div className="text-xl font-bold text-gold-400">
                    +{roi.toLocaleString()}%
                  </div>
                </div>
              </div>

              {/* Fix 1: Honest savings callout — verified math, no inflation */}
              <div className="mb-6 p-4 rounded-xl bg-[#0d3d3d]/60 border border-[#D4AF37]/20 text-left">
                <p className="text-[#D4AF37] text-xs font-bold uppercase tracking-wider mb-1">
                  Honest baseline (RM299/mo plan)
                </p>
                <p className="text-white text-sm font-bold">
                  Save <span className="text-[#D4AF37]">RM2,700+ every month</span> vs a part-time WhatsApp staff.
                </p>
                <p className="text-gray-400 text-xs mt-1">
                  That's <strong className="text-white">~900% ROI</strong> at our RM299 price.
                  Math that holds up when your accountant runs PayScale.
                </p>
                <p className="text-gray-600 text-[10px] mt-1 italic">
                  Jimat <strong>RM2,700+</strong> sebulan berbanding pekerja separuh masa. ROI ~900% pada harga RM299.
                </p>
              </div>

              <button
                onClick={onOpenModal}
                className="block w-full bg-gradient-to-r from-gold-500 to-gold-300 hover:from-gold-400 hover:to-gold-300 text-black font-bold py-4 rounded-xl shadow-[0_0_20px_rgba(212,175,55,0.3)] transition-all transform hover:scale-[1.02] text-center"
              >
                Recover This Revenue Now
              </button>
              <p className="text-xs text-gray-500 mt-4">
                Based on &lt;1s response time and 24/7 availability.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
