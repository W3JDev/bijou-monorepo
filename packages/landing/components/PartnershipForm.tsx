import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Send, Handshake, X } from 'lucide-react';
import { trackFormSubmission } from '../utils/analytics';

interface PartnershipFormProps {
  onClose: () => void;
}

export const PartnershipForm: React.FC<PartnershipFormProps> = ({ onClose }) => {
  const { t, i18n } = useTranslation();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    partnerType: 'property',
    message: ''
  });
  const [status, setStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('sending');

    try {
      const partnerTypeLabels = {
        property: 'Property Agent Network',
        healthcare: 'Healthcare/Dental Association',
        influencer: 'Tech Influencer/YouTuber',
        other: 'Other Partnership'
      };

      const subject = encodeURIComponent(`Partnership Inquiry: ${partnerTypeLabels[formData.partnerType as keyof typeof partnerTypeLabels]} - ${formData.company}`);
      const body = encodeURIComponent(`
Name: ${formData.name}
Email: ${formData.email}
Company: ${formData.company}
Phone: ${formData.phone}
Partnership Type: ${partnerTypeLabels[formData.partnerType as keyof typeof partnerTypeLabels]}

Message:
${formData.message}

---
Partnership Program Details:

PROPERTY NETWORKS:
- RM50 recurring commission per active agent
- Agents get 50% discount (RM99/month instead of RM199)
- Solve RM300k/year lead leakage problem

HEALTHCARE/DENTAL:
- RM30 per signup affiliate fee
- 30-day extended trial + priority support
- Native CMS integration (ClinicPro, Klinik Manager)
- 75% reduction in no-shows

TECH INFLUENCERS:
- Free Lifetime Bijou Pro Account (RM399/month value)
- RM100 per customer referral bounty
- Exclusive "First Manglish AI Agent" content

Sent from Bijou AI Partnership Form
      `);

      // Send to Mr. J (sales/partnerships email)
      window.location.href = `mailto:mrj@mybijou.xyz?subject=${subject}&body=${body}`;

      console.log('Partnership inquiry submitted:', formData);
      
      // Track form submission in Google Analytics
      trackFormSubmission('partnership', i18n.language);
      
      setStatus('success');
      
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (error) {
      console.error('Error submitting form:', error);
      setStatus('error');
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

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
        className="glass-panel-3d max-w-2xl w-full p-8 relative max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-6 h-6" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <Handshake className="w-8 h-8 text-gold-400" />
          <div>
            <h2 className="text-2xl font-bold text-white">{t('contact.partnership.title')}</h2>
            <p className="text-gray-400 text-sm">{t('contact.partnership.subtitle')}</p>
          </div>
        </div>

        {status === 'success' ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Send className="w-8 h-8 text-emerald-400" />
            </div>
            <p className="text-emerald-400 text-lg font-semibold">{t('form.success')}</p>
            <p className="text-gray-400 text-sm mt-2">Mr. J will review your partnership proposal</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="bg-deep-green-500/20 border border-gold-400/30 rounded-lg p-4 mb-6">
              <h3 className="text-gold-400 font-semibold mb-2">Partnership Benefits:</h3>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>🏢 Property Networks: RM50 recurring commission + 50% agent discount</li>
                <li>🏥 Healthcare: RM30/signup + 30-day trial + CMS integration</li>
                <li>📱 Tech Influencers: Free Pro account + RM100/customer bounty</li>
              </ul>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t('form.name')} *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-lg text-white focus:border-gold-400 focus:outline-none transition-colors"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t('form.email')} *
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-lg text-white focus:border-gold-400 focus:outline-none transition-colors"
                  placeholder="john@company.com"
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t('form.company')} *
                </label>
                <input
                  type="text"
                  name="company"
                  value={formData.company}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-lg text-white focus:border-gold-400 focus:outline-none transition-colors"
                  placeholder="IQI Realty / MDA / Tech Channel"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t('form.phone')}
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-lg text-white focus:border-gold-400 focus:outline-none transition-colors"
                  placeholder="+60 17-410 6981"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Partnership Type *
              </label>
              <select
                name="partnerType"
                value={formData.partnerType}
                onChange={handleChange}
                required
                className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-lg text-white focus:border-gold-400 focus:outline-none transition-colors"
              >
                <option value="property">Property Agent Network</option>
                <option value="healthcare">Healthcare/Dental Association</option>
                <option value="influencer">Tech Influencer/YouTuber</option>
                <option value="other">Other Partnership</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('form.message')} *
              </label>
              <textarea
                name="message"
                value={formData.message}
                onChange={handleChange}
                required
                rows={5}
                className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-lg text-white focus:border-gold-400 focus:outline-none transition-colors resize-none"
                placeholder="Tell us about your network size, audience, or association membership..."
              />
            </div>

            {status === 'error' && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
                {t('form.error')} mrj@mybijou.xyz
              </div>
            )}

            <button
              type="submit"
              disabled={status === 'sending'}
              className="w-full px-6 py-4 bg-gradient-to-r from-gold-400 to-gold-500 hover:from-gold-500 hover:to-gold-600 text-black font-semibold rounded-lg transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Send className="w-5 h-5" />
              {status === 'sending' ? t('form.sending') : 'Submit Partnership Inquiry'}
            </button>
          </form>
        )}
      </motion.div>
    </motion.div>
  );
};
