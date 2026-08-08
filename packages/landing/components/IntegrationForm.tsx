import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Send, Puzzle, X } from 'lucide-react';
import { trackFormSubmission } from '../utils/analytics';

interface IntegrationFormProps {
  onClose: () => void;
}

export const IntegrationForm: React.FC<IntegrationFormProps> = ({ onClose }) => {
  const { t, i18n } = useTranslation();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    integration: 'shopify',
    message: ''
  });
  const [status, setStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('sending');

    try {
      const integrationLabels = {
        shopify: 'Shopify E-commerce',
        woocommerce: 'WooCommerce',
        calendly: 'Calendly / Google Calendar',
        clinicpro: 'ClinicPro / Klinik Manager',
        hubspot: 'HubSpot CRM',
        salesforce: 'Salesforce',
        zapier: 'Zapier Automation',
        custom: 'Custom Integration'
      };

      const subject = encodeURIComponent(`Integration Request: ${integrationLabels[formData.integration as keyof typeof integrationLabels]} - ${formData.company}`);
      const body = encodeURIComponent(`
Name: ${formData.name}
Email: ${formData.email}
Company: ${formData.company}
Phone: ${formData.phone}
Requested Integration: ${integrationLabels[formData.integration as keyof typeof integrationLabels]}

Message:
${formData.message}

---
Integration Details:

CURRENT SUPPORTED INTEGRATIONS:
✅ WhatsApp Business API (Native)
✅ ClinicPro / Klinik Manager (Healthcare CMS)
✅ Google Calendar / Calendly (Appointments)
✅ Shopify / WooCommerce (E-commerce)
✅ Zapier (1000+ apps)

PRIORITY SUPPORT: 24-hour response time
CUSTOM DEVELOPMENT: Available for Enterprise plans

Sent from Bijou AI Integration Request Form
      `);

      // Send to support@mybijou.xyz
      window.location.href = `mailto:support@mybijou.xyz?subject=${subject}&body=${body}`;

      console.log('Integration request submitted:', formData);
      
      // Track form submission in Google Analytics
      trackFormSubmission('integration', i18n.language);
      
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
        style={{
          background: '#0A1E1C',
          border: '2px solid #C9A961',
          borderRadius: '16px',
          boxShadow: '0 0 40px rgba(0,0,0,0.6), 0 0 80px rgba(46,241,157,0.08)'
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
          <Puzzle className="w-8 h-8 text-emerald-400" />
          <div>
            <h2 className="text-2xl font-bold text-white" style={{ textShadow: '0 0 20px rgba(46,241,157,0.3)' }}>
              {t('contact.integration.title')}
            </h2>
            <p className="text-gold-400 text-sm">{t('contact.integration.subtitle')}</p>
          </div>
        </div>

        {status === 'success' ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
                 style={{ background: 'rgba(46, 241, 157, 0.15)', border: '2px solid #2EF19D' }}>
              <Send className="w-8 h-8 text-emerald-400" />
            </div>
            <p className="text-emerald-400 text-lg font-semibold">{t('form.success')}</p>
            <p className="text-gray-400 text-sm mt-2">Our team will review your integration request within 24 hours</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="border-2 border-gold-400/30 rounded-lg p-4 mb-6"
                 style={{ background: 'rgba(201, 169, 97, 0.05)', backdropFilter: 'blur(10px)' }}>
              <h3 className="text-gold-400 font-semibold mb-2">Currently Supported:</h3>
              <ul className="text-sm text-white space-y-1">
                <li>✅ Shopify & WooCommerce (E-commerce)</li>
                <li>✅ ClinicPro & Klinik Manager (Healthcare)</li>
                <li>✅ Google Calendar & Calendly (Scheduling)</li>
                <li>✅ Zapier (1000+ apps)</li>
              </ul>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  {t('form.name')} *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '2px solid #2EF19D',
                    backdropFilter: 'blur(10px)'
                  }}
                  className="w-full px-4 py-3 rounded-lg text-white focus:border-cyan-400 focus:outline-none transition-colors focus:shadow-[0_0_15px_rgba(46,241,157,0.3)]"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  {t('form.email')} *
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '2px solid #2EF19D',
                    backdropFilter: 'blur(10px)'
                  }}
                  className="w-full px-4 py-3 rounded-lg text-white focus:border-cyan-400 focus:outline-none transition-colors focus:shadow-[0_0_15px_rgba(46,241,157,0.3)]"
                  placeholder="john@company.com"
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  {t('form.company')} *
                </label>
                <input
                  type="text"
                  name="company"
                  value={formData.company}
                  onChange={handleChange}
                  required
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '2px solid #2EF19D',
                    backdropFilter: 'blur(10px)'
                  }}
                  className="w-full px-4 py-3 rounded-lg text-white focus:border-cyan-400 focus:outline-none transition-colors focus:shadow-[0_0_15px_rgba(46,241,157,0.3)]"
                  placeholder="ABC Clinic / XYZ Shop"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  {t('form.phone')}
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '2px solid #2EF19D',
                    backdropFilter: 'blur(10px)'
                  }}
                  className="w-full px-4 py-3 rounded-lg text-white focus:border-cyan-400 focus:outline-none transition-colors focus:shadow-[0_0_15px_rgba(46,241,157,0.3)]"
                  placeholder="+60 17-410 6981"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Integration Needed *
              </label>
              <select
                name="integration"
                value={formData.integration}
                onChange={handleChange}
                required
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '2px solid #2EF19D',
                  backdropFilter: 'blur(10px)'
                }}
                className="w-full px-4 py-3 rounded-lg text-white focus:border-cyan-400 focus:outline-none transition-colors focus:shadow-[0_0_15px_rgba(46,241,157,0.3)]"
              >
                <option value="shopify" className="bg-[#0A1E1C]">Shopify E-commerce</option>
                <option value="woocommerce" className="bg-[#0A1E1C]">WooCommerce</option>
                <option value="calendly" className="bg-[#0A1E1C]">Calendly / Google Calendar</option>
                <option value="clinicpro" className="bg-[#0A1E1C]">ClinicPro / Klinik Manager</option>
                <option value="hubspot" className="bg-[#0A1E1C]">HubSpot CRM</option>
                <option value="salesforce" className="bg-[#0A1E1C]">Salesforce</option>
                <option value="zapier" className="bg-[#0A1E1C]">Zapier Automation</option>
                <option value="custom" className="bg-[#0A1E1C]">Custom Integration</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-white mb-2">
                {t('form.message')} *
              </label>
              <textarea
                name="message"
                value={formData.message}
                onChange={handleChange}
                required
                rows={5}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '2px solid #2EF19D',
                  backdropFilter: 'blur(10px)'
                }}
                className="w-full px-4 py-3 rounded-lg text-white focus:border-cyan-400 focus:outline-none transition-colors resize-none focus:shadow-[0_0_15px_rgba(46,241,157,0.3)]"
                placeholder="Describe your integration needs and use case..."
              />
            </div>

            {status === 'error' && (
              <div className="rounded-lg p-4 text-sm"
                   style={{ background: 'rgba(255, 107, 107, 0.15)', border: '1px solid #FF6B6B', color: '#FF6B6B' }}>
                {t('form.error')} support@mybijou.xyz
              </div>
            )}

            <button
              type="submit"
              disabled={status === 'sending'}
              style={{
                background: 'linear-gradient(135deg, #2EF19D 0%, #00F5E4 100%)',
                boxShadow: '0 4px 15px rgba(46,241,157,0.25)'
              }}
              className="w-full px-6 py-4 text-[#0A1E1C] font-bold rounded-lg transition-all transform hover:scale-105 hover:shadow-[0_6px_25px_rgba(46,241,157,0.4)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Send className="w-5 h-5" />
              {status === 'sending' ? t('form.sending') : t('form.submit')}
            </button>
          </form>
        )}
      </motion.div>
    </motion.div>
  );
};
