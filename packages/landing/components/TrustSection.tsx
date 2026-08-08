import React from 'react';
import { motion } from 'framer-motion';
import { PhoneOff, Clock, TrendingDown } from 'lucide-react';

export const TrustSection: React.FC = () => {
  return (
    <section id="trust" className="py-20 border-y border-white/5 bg-black/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-3 gap-8">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0 }}
            className="text-center p-6"
          >
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-500/10 mb-6 text-red-500">
              <PhoneOff className="w-8 h-8" />
            </div>
            <h3 className="text-4xl font-bold text-white mb-2">50%</h3>
            <p className="text-lg font-medium text-red-400 mb-2">Missed Call Loss</p>
            <p className="text-sm text-gray-500">
              Real Estate agents lose half their leads simply by being busy on other calls.
            </p>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-center p-6 border-l border-r border-white/5"
          >
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-orange-500/10 mb-6 text-orange-500">
              <TrendingDown className="w-8 h-8" />
            </div>
            <h3 className="text-4xl font-bold text-white mb-2">31.5%</h3>
            <p className="text-lg font-medium text-orange-400 mb-2">Healthcare No-Shows</p>
            <p className="text-sm text-gray-500">
              Clinics bleed revenue when patients book and forget. Bijou chases them.
            </p>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="text-center p-6"
          >
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/10 mb-6 text-emerald-500">
              <Clock className="w-8 h-8" />
            </div>
            <h3 className="text-4xl font-bold text-white mb-2">0s</h3>
            <p className="text-lg font-medium text-emerald-400 mb-2">Response Time</p>
            <p className="text-sm text-gray-500">
              Instant replies, 24/7. While you sleep, Bijou is closing deals.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
};