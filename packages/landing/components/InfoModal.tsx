import { motion } from "framer-motion";
import { Building2, FileText, Shield, Users, X } from "lucide-react";
import React from "react";

interface InfoModalProps {
  type: "about" | "careers" | "privacy" | "terms";
  onClose: () => void;
}

export const InfoModal: React.FC<InfoModalProps> = ({ type, onClose }) => {
  const content = {
    about: {
      icon: <Building2 className="w-8 h-8 text-gold-400" />,
      title: "About Bijou AI",
      content: (
        <>
          <p className="text-gray-300 mb-4">
            Bijou AI is a production of{" "}
            <strong className="text-gold-400">W3J LLC</strong>, a Wyoming-based
            technology company with operations in Kuala Lumpur, Malaysia.
          </p>
          <p className="text-gray-300 mb-4">
            We're on a mission to bring AI-powered customer service to Malaysian
            SMEs through WhatsApp - the platform your customers already use
            every day.
          </p>
          <div className="bg-deep-green-500/20 border border-gold-400/30 rounded-lg p-4 mb-4">
            <h3 className="text-gold-400 font-semibold mb-2">Our Vision</h3>
            <p className="text-gray-300 text-sm">
              Stop losing RM300k/year to late-night WhatsApp leads. Bijou AI
              speaks fluent Manglish and closes sales 24/7 for Malaysian
              businesses.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <strong className="text-emerald-400">🏢 Company:</strong>
              <p className="text-gray-400">W3J LLC - Wyoming, USA</p>
            </div>
            <div>
              <strong className="text-emerald-400">📍 Operations:</strong>
              <p className="text-gray-400">Kuala Lumpur, Malaysia</p>
            </div>
            <div>
              <strong className="text-emerald-400">👨‍💼 Founder:</strong>
              <p className="text-gray-400">Muhammad Nurunnabi (Jewel)</p>
            </div>
            <div>
              <strong className="text-emerald-400">🌐 Website:</strong>
              <p className="text-gray-400">
                <a
                  href="https://www.w3jdev.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gold-400 hover:text-gold-300"
                >
                  w3jdev.com
                </a>
              </p>
            </div>
          </div>
        </>
      ),
    },
    careers: {
      icon: <Users className="w-8 h-8 text-gold-400" />,
      title: "Careers at Bijou AI",
      content: (
        <>
          <p className="text-gray-300 mb-4">
            Join us in revolutionizing customer service for Malaysian
            businesses!
          </p>
          <div className="bg-deep-green-500/20 border border-gold-400/30 rounded-lg p-4 mb-4">
            <h3 className="text-gold-400 font-semibold mb-2">
              🚀 We're Growing!
            </h3>
            <p className="text-gray-300 text-sm">
              Bijou AI is currently in rapid growth mode. We're looking for
              passionate individuals who want to make an impact in the AI and
              SME space.
            </p>
          </div>
          <div className="space-y-3 mb-4">
            <div>
              <strong className="text-emerald-400">🔍 Open Positions:</strong>
              <p className="text-gray-400 text-sm mt-1">
                Currently building our founding team. Check back soon for open
                roles!
              </p>
            </div>
            <div>
              <strong className="text-emerald-400">💼 Work Culture:</strong>
              <p className="text-gray-400 text-sm mt-1">
                Remote-first, flexible hours, high-impact work
              </p>
            </div>
            <div>
              <strong className="text-emerald-400">📧 Interested?</strong>
              <p className="text-gray-400 text-sm mt-1">
                Send your resume to{" "}
                <a
                  href="mailto:jewel@mybijou.xyz"
                  className="text-gold-400 hover:text-gold-300"
                >
                  jewel@mybijou.xyz
                </a>
              </p>
            </div>
          </div>
        </>
      ),
    },
    privacy: {
      icon: <Shield className="w-8 h-8 text-gold-400" />,
      title: "Privacy Policy",
      content: (
        <>
          <p className="text-gray-300 mb-4">
            <strong>Last Updated:</strong> February 24, 2026
          </p>
          <div className="space-y-4 text-sm text-gray-300">
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">
                Data Collection
              </h3>
              <p>
                Bijou AI collects only the data necessary to provide our
                WhatsApp AI service:
              </p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-gray-400">
                <li>Business contact information (name, email, phone)</li>
                <li>WhatsApp conversation data for AI training</li>
                <li>Usage analytics for service improvement</li>
              </ul>
            </div>
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">
                Data Security
              </h3>
              <p className="text-gray-400">
                All data is encrypted at rest and in transit. We use
                industry-standard security measures to protect your information.
              </p>
            </div>
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">
                Third-Party Services
              </h3>
              <p className="text-gray-400">
                We use Supabase (PostgreSQL database), Google Gemini AI, and
                WhatsApp Business API. All comply with GDPR and data protection
                standards.
              </p>
            </div>
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">
                Your Rights
              </h3>
              <p className="text-gray-400">
                You have the right to access, modify, or delete your data at any
                time. Contact{" "}
                <a
                  href="mailto:support@mybijou.xyz"
                  className="text-gold-400 hover:text-gold-300"
                >
                  support@mybijou.xyz
                </a>{" "}
                for requests.
              </p>
            </div>
          </div>
        </>
      ),
    },
    terms: {
      icon: <FileText className="w-8 h-8 text-gold-400" />,
      title: "Terms of Service",
      content: (
        <>
          <p className="text-gray-300 mb-4">
            <strong>Last Updated:</strong> February 24, 2026
          </p>
          <div className="space-y-4 text-sm text-gray-300">
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">
                Service Agreement
              </h3>
              <p className="text-gray-400">
                By using Bijou AI, you agree to use our WhatsApp AI service in
                compliance with WhatsApp Business API policies and Malaysian
                laws.
              </p>
            </div>
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">
                Subscription Terms
              </h3>
              <ul className="list-disc list-inside space-y-1 text-gray-400">
                <li>30-day money-back guarantee (no credit card at signup)</li>
                <li>
                  Monthly billing at RM299/month (PRO plan) or RM2,990/year
                  (save RM598)
                </li>
                <li>Cancel anytime — no minimum contract</li>
                <li>Refunds available within 30 days of first payment</li>
              </ul>
            </div>
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">
                Acceptable Use
              </h3>
              <p className="text-gray-400">
                You agree not to use Bijou AI for spam, illegal activities, or
                content that violates WhatsApp's Terms of Service.
              </p>
            </div>
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">Liability</h3>
              <p className="text-gray-400">
                Bijou AI provides service "as-is". We are not liable for lost
                revenue due to service downtime. See SLA for uptime guarantees.
              </p>
            </div>
            <div>
              <h3 className="text-emerald-400 font-semibold mb-2">
                Questions?
              </h3>
              <p className="text-gray-400">
                Contact{" "}
                <a
                  href="mailto:jewel@mybijou.xyz"
                  className="text-gold-400 hover:text-gold-300"
                >
                  jewel@mybijou.xyz
                </a>{" "}
                for legal inquiries.
              </p>
            </div>
          </div>
        </>
      ),
    },
  };

  const { icon, title, content: modalContent } = content[type];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        style={{
          background: "#0A1E1C",
          border: "2px solid #C9A961",
          borderRadius: "16px",
          boxShadow: "0 0 40px rgba(0,0,0,0.6), 0 0 80px rgba(46,241,157,0.08)",
        }}
        className="max-w-2xl w-full p-8 relative max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-6 h-6" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          {icon}
          <h2
            className="text-2xl font-bold text-white"
            style={{ textShadow: "0 0 20px rgba(46,241,157,0.3)" }}
          >
            {title}
          </h2>
        </div>

        <div className="prose prose-invert max-w-none">{modalContent}</div>

        <div className="mt-8 pt-6 border-t border-white/10 text-center">
          <button
            onClick={onClose}
            style={{
              background: "linear-gradient(135deg, #2EF19D 0%, #00F5E4 100%)",
              boxShadow: "0 4px 15px rgba(46,241,157,0.25)",
            }}
            className="px-8 py-3 text-[#0A1E1C] font-bold rounded-lg transition-all transform hover:scale-105 hover:shadow-[0_6px_25px_rgba(46,241,157,0.4)]"
          >
            Close
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};
