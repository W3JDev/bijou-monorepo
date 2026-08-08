import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, Video, CheckCircle, ArrowRight } from 'lucide-react';

interface CalBookingProps {
  className?: string;
  onBookingComplete?: (bookingData: any) => void;
}

export const CalBooking: React.FC<CalBookingProps> = ({ 
  className = '',
  onBookingComplete 
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [isBookingComplete, setIsBookingComplete] = useState(false);

  // Cal.com configuration — `import.meta.env` (Vite's runtime contract),
  // not `process.env` (which Vite only sets for NODE_ENV in this config).
  // See audit-report.md finding #17.
  const calUsername = import.meta.env.VITE_PUBLIC_CAL_USERNAME || 'getbijou';
  const calUrl = `https://cal.com/${calUsername}`;

  // Listen for booking completion
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Cal.com sends postMessage when booking is completed
      if (event.origin === 'https://cal.com') {
        if (event.data?.type === 'booking_completed') {
          setIsBookingComplete(true);
          
          // Submit lead to our system
          handleBookingLead(event.data);
          
          if (onBookingComplete) {
            onBookingComplete(event.data);
          }
        }
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onBookingComplete]);

  const handleBookingLead = async (bookingData: any) => {
    try {
      // Log the booking for now - can be sent to proper analytics later
      console.log('✅ Demo booking completed:', {
        name: bookingData.attendee?.name || 'Demo Booking',
        email: bookingData.attendee?.email || '',
        source: 'cal_booking',
        eventType: bookingData.eventType?.title || 'Bijou AI Demo'
      });
    } catch (error) {
      console.error('❌ Failed to log booking:', error);
    }
  };

  const handleIframeLoad = () => {
    setIsLoading(false);
  };

  if (isBookingComplete) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`text-center p-8 glass-panel-3d rounded-2xl border border-emerald-500/30 ${className}`}
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6"
        >
          <CheckCircle className="w-12 h-12 text-emerald-400" />
        </motion.div>
        
        <h3 className="text-2xl font-bold text-white mb-4">
          Swee! Demo Booked! 🎉
        </h3>
        
        <p className="text-gray-300 mb-6 leading-relaxed">
          Terima kasih! Your demo is confirmed. We'll send you a calendar invite and preparation materials via email.
        </p>
        
        <div className="grid md:grid-cols-3 gap-4 text-sm text-gray-400">
          <div className="flex items-center justify-center gap-2">
            <Video className="w-4 h-4 text-emerald-400" />
            <span>Virtual Demo</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <Clock className="w-4 h-4 text-emerald-400" />
            <span>30 Minutes</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>Confirmed</span>
          </div>
        </div>

        <motion.a
          href="https://wa.me/60174106981"
          target="_blank"
          rel="noopener noreferrer"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-emerald-500 text-dark-900 font-semibold rounded-lg hover:bg-emerald-400 transition-colors"
        >
          Questions? WhatsApp Us
          <ArrowRight className="w-4 h-4" />
        </motion.a>
      </motion.div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {/* Header */}
      <div className="text-center mb-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-panel-3d border border-emerald-500/30 text-emerald-400 text-sm font-medium mb-4"
        >
          <Calendar className="w-4 h-4" />
          Book Your Demo
        </motion.div>
        
        <h3 className="text-2xl lg:text-3xl font-bold text-white mb-4">
          See Bijou Close Real Leads
        </h3>
        
        <p className="text-gray-300 max-w-2xl mx-auto leading-relaxed">
          30-minute live demo where you'll watch Bijou handle actual Malaysian customer inquiries in Manglish. 
          No sales pitch, just results.
        </p>
      </div>

      {/* Features */}
      <div className="grid md:grid-cols-3 gap-4 mb-8">
        <div className="flex items-center gap-3 p-4 glass-panel rounded-xl">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
            <Video className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-white font-medium">Live Demo</p>
            <p className="text-gray-400 text-sm">Real scenarios</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3 p-4 glass-panel rounded-xl">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
            <Clock className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-white font-medium">30 Minutes</p>
            <p className="text-gray-400 text-sm">Quick & focused</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3 p-4 glass-panel rounded-xl">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-white font-medium">No Pressure</p>
            <p className="text-gray-400 text-sm">Just results</p>
          </div>
        </div>
      </div>

      {/* Cal.com Embed */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center glass-panel-3d rounded-2xl">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-300">Loading calendar...</p>
            </div>
          </div>
        )}
        
        <div className="glass-panel-3d rounded-2xl overflow-hidden border border-white/10">
          <iframe
            src={`${calUrl}/30min?embed=true&theme=dark&hideEventTypeDetails=false`}
            width="100%"
            height="600"
            frameBorder="0"
            title="Book a Demo with Bijou AI"
            onLoad={handleIframeLoad}
            className="w-full"
          />
        </div>
      </div>

      {/* Trust Indicators */}
      <div className="mt-8 text-center">
        <div className="flex items-center justify-center gap-6 text-sm text-gray-400">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>No credit card required</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>PDPA compliant</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>Cancel anytime</span>
          </div>
        </div>
      </div>
    </div>
  );
};