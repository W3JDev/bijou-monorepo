import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, Copy, Smartphone, QrCode, ArrowRight, Check, X, Loader2, Zap, ChevronDown, Share2, MessageCircle, Facebook, Twitter, AlertCircle, BarChart3, Globe, ExternalLink } from 'lucide-react';
import { linkShortenerService } from '../services/linkShortener';

const COUNTRY_CODES = [
  { code: '+60', country: 'MY', flag: '🇲🇾' },
  { code: '+65', country: 'SG', flag: '🇸🇬' },
  { code: '+62', country: 'ID', flag: '🇮🇩' },
  { code: '+66', country: 'TH', flag: '🇹🇭' },
  { code: '+63', country: 'PH', flag: '🇵🇭' },
  { code: '+84', country: 'VN', flag: '🇻🇳' },
  { code: '+1', country: 'US', flag: '🇺🇸' },
  { code: '+44', country: 'UK', flag: '🇬🇧' },
  { code: '+61', country: 'AU', flag: '🇦🇺' },
];

const MAX_MSG_LENGTH = 300;

export const WhatsAppLinkGenerator: React.FC = () => {
  // Input State
  const [phone, setPhone] = useState('');
  const [countryCode, setCountryCode] = useState<(typeof COUNTRY_CODES)[number]>(COUNTRY_CODES[0]!);
  const [message, setMessage] = useState('');
  const [isTracking, setIsTracking] = useState(false);
  
  // Validation & UI State
  const [phoneError, setPhoneError] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // App Logic State
  const [generatedLink, setGeneratedLink] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  
  // Modal/Backend State
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [trackingId, setTrackingId] = useState('');

  // Click outside listener for dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Helper to sanitize phone number
  const getFormattedPhone = () => {
    const cleaned = phone.replace(/\D/g, '');
    const finalNumber = cleaned.startsWith('0') ? cleaned.substring(1) : cleaned;
    return `${countryCode.code.replace('+', '')}${finalNumber}`;
  };

  const validateInputs = () => {
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.length < 5) {
      setPhoneError('Please enter a valid phone number');
      return false;
    }
    setPhoneError('');
    return true;
  };

  const handleGenerateClick = () => {
    if (!validateInputs()) return;

    if (isTracking) {
      setShowModal(true);
    } else {
      generateStandardLink();
    }
  };

  const generateStandardLink = () => {
    const number = getFormattedPhone();
    const text = encodeURIComponent(message);
    const link = `https://wa.me/${number}?text=${text}`;
    setGeneratedLink(link);
    setTrackingId(''); // No tracking for standard links
    setShowResult(true);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedLink);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleShare = (platform: 'whatsapp' | 'twitter' | 'facebook') => {
    const text = encodeURIComponent("Check out this link: ");
    const url = encodeURIComponent(generatedLink);
    
    let shareUrl = '';
    switch (platform) {
      case 'whatsapp':
        shareUrl = `https://wa.me/?text=${text}${url}`;
        break;
      case 'twitter':
        shareUrl = `https://twitter.com/intent/tweet?url=${url}&text=${text}`;
        break;
      case 'facebook':
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
        break;
    }
    window.open(shareUrl, '_blank');
  };

  const handleSubmitTracking = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);

    try {
      // Use the Service Layer to simulate (or perform) the "Real Power"
      const result = await linkShortenerService.createLink({
        phone: getFormattedPhone(),
        message: message,
        email: email
      });
      
      setGeneratedLink(result.shortLink);
      setTrackingId(result.trackingId);
      setIsSuccess(true);
      
      setTimeout(() => {
        setShowModal(false);
        setShowResult(true);
        setIsSuccess(false);
        setIsLoading(false);
      }, 1500);

    } catch (error) {
      console.error(error);
      setIsLoading(false);
    }
  };

  return (
    <section className="py-24 relative">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-4">
            <Smartphone className="w-3 h-3" />
            Free Tool
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Smart WhatsApp Link Generator
          </h2>
          <p className="text-gray-400">
            Create a custom link for your customers to message you instantly.
          </p>
        </div>

        {/* Main Card */}
        <div className="glass-panel-3d rounded-3xl p-8 border border-white/10 relative overflow-hidden">
          
          <div className="grid md:grid-cols-2 gap-12">
            
            {/* Input Section */}
            <div className="space-y-6">
              
              {/* Phone Input */}
              <div className="relative z-20">
                <label className="block text-sm font-medium text-gray-300 mb-2">WhatsApp Number</label>
                <div className="flex relative">
                  {/* Country Code Dropdown */}
                  <div className="relative" ref={dropdownRef}>
                    <button
                      type="button"
                      onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                      className="h-full inline-flex items-center gap-2 px-3 rounded-l-xl border border-r-0 border-white/10 bg-white/5 text-gray-300 font-mono text-sm hover:bg-white/10 transition-colors min-w-[100px]"
                    >
                      <span>{countryCode.flag}</span>
                      <span>{countryCode.code}</span>
                      <ChevronDown className="w-3 h-3 ml-auto opacity-50" />
                    </button>
                    
                    <AnimatePresence>
                      {isDropdownOpen && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 10 }}
                          className="absolute top-full left-0 mt-2 w-48 bg-dark-800 border border-white/10 rounded-xl shadow-xl overflow-hidden max-h-60 overflow-y-auto z-50"
                        >
                          {COUNTRY_CODES.map((country) => (
                            <button
                              key={country.code + country.country}
                              onClick={() => {
                                setCountryCode(country);
                                setIsDropdownOpen(false);
                              }}
                              className={`w-full text-left px-4 py-3 text-sm flex items-center gap-3 hover:bg-white/5 transition-colors ${
                                countryCode.code === country.code ? 'bg-emerald-500/10 text-emerald-400' : 'text-gray-300'
                              }`}
                            >
                              <span className="text-lg">{country.flag}</span>
                              <span className="font-mono opacity-70">{country.code}</span>
                              <span className="text-xs font-bold ml-auto opacity-50">{country.country}</span>
                            </button>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => {
                      setPhone(e.target.value);
                      if (phoneError) setPhoneError('');
                    }}
                    placeholder="12 345 6789"
                    className={`flex-1 min-w-0 block w-full px-4 py-3 rounded-r-xl bg-black/40 border text-white placeholder-gray-600 focus:outline-none focus:ring-1 transition-all font-mono ${
                      phoneError 
                        ? 'border-red-500 focus:border-red-500 focus:ring-red-500' 
                        : 'border-white/10 focus:ring-emerald-500 focus:border-emerald-500'
                    }`}
                  />
                </div>
                {phoneError && (
                  <div className="flex items-center gap-1.5 mt-2 text-red-400 text-xs animate-pulse">
                    <AlertCircle className="w-3 h-3" />
                    {phoneError}
                  </div>
                )}
              </div>

              {/* Message Input */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Pre-filled Message <span className="text-gray-600 text-xs ml-2">(Optional)</span>
                </label>
                <div className="relative">
                  <textarea
                    rows={4}
                    value={message}
                    maxLength={MAX_MSG_LENGTH}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Hi! I'm interested in..."
                    className="block w-full px-4 py-3 rounded-xl bg-black/40 border border-white/10 text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-all resize-none"
                  />
                  <div className={`absolute bottom-3 right-3 text-[10px] font-medium ${
                    message.length >= MAX_MSG_LENGTH ? 'text-red-400' : 'text-gray-600'
                  }`}>
                    {message.length}/{MAX_MSG_LENGTH}
                  </div>
                </div>
              </div>

              {/* The "Clever Move" Checkbox */}
              <div 
                className={`p-4 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                  isTracking 
                    ? 'bg-emerald-900/10 border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.1)]' 
                    : 'bg-white/5 border-white/10 hover:bg-white/10'
                }`}
                onClick={() => setIsTracking(!isTracking)}
              >
                <div className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                  isTracking ? 'bg-emerald-500 border-emerald-500' : 'border-gray-500'
                }`}>
                  {isTracking && <Check className="w-3.5 h-3.5 text-black" />}
                </div>
                <div>
                  <div className="text-sm font-bold text-white flex items-center gap-2">
                    Track clicks with Bijou AI
                    <span className="text-[10px] bg-emerald-500 text-black px-1.5 py-0.5 rounded font-bold uppercase">Free Trial</span>
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Get analytics on who clicks your link and capture leads automatically.
                  </div>
                </div>
              </div>

              <button
                onClick={handleGenerateClick}
                disabled={!phone}
                className="w-full bg-white text-dark-900 hover:bg-gray-200 font-bold py-4 rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group"
              >
                <Zap className="w-5 h-5 fill-dark-900 group-hover:scale-110 transition-transform" />
                Generate Link
              </button>
            </div>

            {/* Output Section */}
            <div className="flex flex-col items-center justify-center bg-black/20 rounded-2xl border border-white/5 p-8 relative min-h-[400px]">
              {!showResult ? (
                <div className="text-center text-gray-500">
                  <QrCode className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p className="text-sm">Enter details to generate your<br/>Smart WhatsApp Link</p>
                </div>
              ) : (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="w-full flex flex-col items-center"
                >
                  {/* Result Card */}
                  <div className="bg-white p-4 rounded-2xl shadow-lg mb-6 group relative">
                    <img 
                      src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(generatedLink)}&bgcolor=ffffff&color=000000`}
                      alt="WhatsApp QR Code"
                      className="w-40 h-40 mix-blend-multiply" 
                    />
                  </div>

                  {/* Link Box */}
                  <div className="w-full bg-black/40 rounded-xl border border-white/10 p-1 flex items-center gap-2 mb-6">
                    <div className="flex-1 px-3 py-2 text-sm text-gray-300 font-mono truncate">
                      {generatedLink}
                    </div>
                    <button 
                      onClick={handleCopy}
                      className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors relative group"
                      title="Copy Link"
                    >
                      {isCopied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 group-hover:scale-110 transition-transform" />}
                    </button>
                  </div>

                  {/* Visual Feedback for "Power" Mode (Tracking) */}
                  {trackingId ? (
                     <div className="w-full bg-emerald-900/10 border border-emerald-500/20 rounded-xl p-4 mb-4">
                        <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-3">
                           <BarChart3 className="w-4 h-4" />
                           Live Analytics Preview
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                           <div className="bg-black/40 rounded-lg p-2 border border-white/5">
                              <div className="text-[10px] text-gray-500">Clicks</div>
                              <div className="text-lg font-mono font-bold text-white">0</div>
                           </div>
                           <div className="bg-black/40 rounded-lg p-2 border border-white/5">
                              <div className="text-[10px] text-gray-500">Status</div>
                              <div className="text-xs font-bold text-emerald-400 flex items-center gap-1 mt-1">
                                 <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Active
                              </div>
                           </div>
                        </div>
                        <div className="mt-3 text-[10px] text-gray-500 text-center flex items-center justify-center gap-1">
                           Link ID: <span className="font-mono text-gray-400">{trackingId}</span>
                           <ExternalLink className="w-3 h-3 ml-1" />
                        </div>
                     </div>
                  ) : (
                    /* Social Sharing for Standard Mode */
                    <div className="grid grid-cols-3 gap-3 w-full">
                       <button 
                         onClick={() => handleShare('whatsapp')}
                         className="flex items-center justify-center gap-2 p-3 rounded-xl bg-[#25D366]/20 border border-[#25D366]/30 text-[#25D366] hover:bg-[#25D366]/30 transition-all"
                         title="Share on WhatsApp"
                       >
                          <MessageCircle className="w-5 h-5" />
                       </button>
                       <button 
                         onClick={() => handleShare('twitter')}
                         className="flex items-center justify-center gap-2 p-3 rounded-xl bg-blue-400/20 border border-blue-400/30 text-blue-400 hover:bg-blue-400/30 transition-all"
                         title="Share on X (Twitter)"
                       >
                          <Twitter className="w-5 h-5" />
                       </button>
                       <button 
                         onClick={() => handleShare('facebook')}
                         className="flex items-center justify-center gap-2 p-3 rounded-xl bg-blue-600/20 border border-blue-600/30 text-blue-600 hover:bg-blue-600/30 transition-all"
                         title="Share on Facebook"
                       >
                          <Facebook className="w-5 h-5" />
                       </button>
                    </div>
                  )}

                </motion.div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Lead Capture Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
              onClick={() => !isLoading && setShowModal(false)}
            />
            
            <motion.div 
              initial={{ opacity: 0, y: 50 }} 
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="relative w-full max-w-md bg-dark-800 border border-white/10 rounded-3xl p-8 shadow-2xl overflow-hidden"
            >
              {/* Success Overlay */}
              {isSuccess && (
                <div className="absolute inset-0 bg-emerald-900/90 z-20 flex flex-col items-center justify-center text-center p-8">
                  <div className="w-16 h-16 bg-emerald-500 rounded-full flex items-center justify-center mb-4 shadow-[0_0_30px_rgba(16,185,129,0.5)]">
                    <Check className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-2">Success!</h3>
                  <p className="text-emerald-100">Your tracked link is ready.</p>
                </div>
              )}

              <div className="text-center mb-8">
                <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-blue-500 rounded-xl mx-auto flex items-center justify-center mb-4 shadow-lg">
                  <Link className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-2">Unlock Link Tracking</h3>
                <p className="text-gray-400 text-sm">
                  Enter your email to activate your free tracking dashboard and see who clicks your link.
                </p>
              </div>

              <form onSubmit={handleSubmitTracking} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Business Email</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="w-full px-4 py-3 rounded-xl bg-black/50 border border-white/10 text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-all"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-emerald-500 to-emerald-400 text-dark-900 font-bold py-4 rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] transition-all flex items-center justify-center gap-2 disabled:opacity-80"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Creating Account...
                    </>
                  ) : (
                    <>
                      Start My Free Trial
                      <ArrowRight className="w-5 h-5" />
                    </>
                  )}
                </button>
                
                <p className="text-center text-[10px] text-gray-600">
                  By continuing, you agree to our Terms of Service. No credit card required.
                </p>
              </form>
              
              <button 
                onClick={() => setShowModal(false)}
                className="absolute top-4 right-4 text-gray-500 hover:text-white transition-colors"
                disabled={isLoading}
              >
                <X className="w-5 h-5" />
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </section>
  );
};