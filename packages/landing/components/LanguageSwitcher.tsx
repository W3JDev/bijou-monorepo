import type React from 'react';

// US/EU pivot: the site is English-only, so the language switcher is hidden.
// Kept as a no-op component so existing imports (e.g. Navbar) keep working.
export const LanguageSwitcher: React.FC = () => null;
