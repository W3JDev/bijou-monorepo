import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe } from 'lucide-react';
import { trackLanguageChange } from '../utils/analytics';

export const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const languages = [
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'ms', name: 'Bahasa Melayu', flag: '🇲🇾' },
    { code: 'zh', name: '简体中文', flag: '🇨🇳' },
    { code: 'ta', name: 'தமிழ்', flag: '🇮🇳' }
  ];

  const currentLanguage = languages.find(lang => lang.code === i18n.language) || languages[0]!;

  const changeLanguage = (languageCode: string) => {
    i18n.changeLanguage(languageCode);
    trackLanguageChange(languageCode);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-white hover:bg-deep-green-500/30 transition-colors border border-white/10"
      >
        <Globe className="w-4 h-4" />
        <span className="hidden md:inline text-sm">{currentLanguage.flag} {currentLanguage.name}</span>
        <span className="md:hidden text-sm">{currentLanguage.flag}</span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Dropdown */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute right-0 mt-2 w-56 rounded-lg shadow-lg z-50"
              style={{
                background: '#0A1E1C',
                border: '2px solid #C9A961',
                boxShadow: '0 0 40px rgba(0,0,0,0.6), 0 0 80px rgba(46,241,157,0.08)'
              }}
            >
              <div className="p-2">
                {languages.map((language) => (
                  <button
                    key={language.code}
                    onClick={() => changeLanguage(language.code)}
                    className={`w-full text-left px-4 py-3 rounded-lg transition-colors flex items-center gap-3 ${
                      i18n.language === language.code
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'text-white hover:bg-white/5'
                    }`}
                  >
                    <span className="text-2xl">{language.flag}</span>
                    <span className="font-medium">{language.name}</span>
                    {i18n.language === language.code && (
                      <span className="ml-auto text-emerald-400">✓</span>
                    )}
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
