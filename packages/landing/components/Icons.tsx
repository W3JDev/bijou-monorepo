import React from 'react';

// Shared Gradients & Filters
const Defs = () => (
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="coloredBlur" />
      <feMerge>
        <feMergeNode in="coloredBlur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <filter id="glass" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="blur" />
      <feOffset in="blur" dx="2" dy="4" result="offsetBlur" />
      <feSpecularLighting in="blur" surfaceScale="5" specularConstant=".75" specularExponent="20" lightingColor="#ffffff" result="specOut">
        <fePointLight x="-5000" y="-10000" z="20000" />
      </feSpecularLighting>
      <feComposite in="specOut" in2="SourceAlpha" operator="in" result="specOut" />
      <feComposite in="SourceGraphic" in2="specOut" operator="arithmetic" k1="0" k2="1" k3="1" k4="0" result="litPaint" />
    </filter>
    <linearGradient id="emeraldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stopColor="#34d399" stopOpacity="0.8" />
      <stop offset="100%" stopColor="#064e3b" stopOpacity="0.9" />
    </linearGradient>
    <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.8" />
      <stop offset="100%" stopColor="#4c1d95" stopOpacity="0.9" />
    </linearGradient>
    <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.8" />
      <stop offset="100%" stopColor="#1e3a8a" stopOpacity="0.9" />
    </linearGradient>
    <linearGradient id="orangeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stopColor="#fbbf24" stopOpacity="0.8" />
      <stop offset="100%" stopColor="#b45309" stopOpacity="0.9" />
    </linearGradient>
    <linearGradient id="glassGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stopColor="white" stopOpacity="0.4" />
      <stop offset="100%" stopColor="white" stopOpacity="0.1" />
    </linearGradient>
  </defs>
);

export const IconCommunication = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 100 100" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    <Defs />
    <g filter="url(#glow)">
      {/* Back Bubble */}
      <path d="M30 25H70C78.2843 25 85 31.7157 85 40V60C85 68.2843 78.2843 75 70 75H65L55 85V75H30C21.7157 75 15 68.2843 15 60V40C15 31.7157 21.7157 25 30 25Z" fill="url(#emeraldGrad)" opacity="0.3" transform="translate(-5, 5)" />
      {/* Front Bubble */}
      <path d="M30 15H70C78.2843 15 85 21.7157 85 30V50C85 58.2843 78.2843 65 70 65H65L55 75V65H30C21.7157 65 15 58.2843 15 50V30C15 21.7157 21.7157 15 30 15Z" fill="url(#emeraldGrad)" />
      {/* Gloss Highlight */}
      <path d="M30 15H70C78.2843 15 85 21.7157 85 30V40C85 35 75 25 30 25C25 25 15 35 15 40V30C15 21.7157 21.7157 15 30 15Z" fill="white" fillOpacity="0.2" />
      {/* Text Lines */}
      <rect x="30" y="35" width="40" height="4" rx="2" fill="white" fillOpacity="0.8" />
      <rect x="30" y="45" width="25" height="4" rx="2" fill="white" fillOpacity="0.6" />
    </g>
  </svg>
);

export const IconIntelligence = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 100 100" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    <Defs />
    <g filter="url(#glow)">
      {/* Outer Eye Shape */}
      <path d="M50 20C75 20 90 40 95 50C90 60 75 80 50 80C25 80 10 60 5 50C10 40 25 20 50 20Z" fill="url(#purpleGrad)" stroke="white" strokeOpacity="0.2" strokeWidth="1" />
      {/* Iris */}
      <circle cx="50" cy="50" r="18" fill="#1f1f1f" stroke="#a78bfa" strokeWidth="2" />
      {/* Pupil/Circuit */}
      <circle cx="50" cy="50" r="8" fill="#a78bfa" />
      <path d="M50 32V20M50 80V68M20 50H32M68 50H80" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" />
      {/* Gloss */}
      <ellipse cx="60" cy="40" rx="8" ry="4" fill="white" fillOpacity="0.3" transform="rotate(-45 60 40)" />
    </g>
  </svg>
);

export const IconAutomation = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 100 100" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    <Defs />
    <g filter="url(#glow)">
      {/* Background shape */}
      <circle cx="50" cy="50" r="35" fill="url(#blueGrad)" opacity="0.2" />
      {/* Lightning Bolt */}
      <path d="M55 15L30 50H50L45 85L70 50H50L55 15Z" fill="url(#blueGrad)" stroke="white" strokeWidth="1" strokeOpacity="0.5" />
      {/* Motion Lines */}
      <path d="M20 40H10" stroke="#60a5fa" strokeWidth="3" strokeLinecap="round" />
      <path d="M25 50H5" stroke="#60a5fa" strokeWidth="3" strokeLinecap="round" opacity="0.7" />
      <path d="M20 60H10" stroke="#60a5fa" strokeWidth="3" strokeLinecap="round" />
    </g>
  </svg>
);

export const IconSecurity = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 100 100" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    <Defs />
    <g filter="url(#glow)">
      {/* Shield */}
      <path d="M50 15L20 25V50C20 68 35 80 50 85C65 80 80 68 80 50V25L50 15Z" fill="url(#orangeGrad)" />
      {/* Keyhole */}
      <circle cx="50" cy="45" r="6" fill="#1f1f1f" />
      <path d="M46 50L44 65H56L54 50" fill="#1f1f1f" />
      {/* Lock Check */}
      <path d="M35 50L45 60L65 40" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      {/* Gloss */}
      <path d="M50 15L20 25V50C20 55 25 60 50 60C75 60 80 55 80 50V25L50 15Z" fill="url(#glassGrad)" opacity="0.5" />
    </g>
  </svg>
);

// Illustrations for Viral Pillars

export const IlluStressTest = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 200 120" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    <Defs />
    {/* Split Background */}
    <rect x="10" y="10" width="180" height="100" rx="10" fill="#1a1a1a" stroke="white" strokeOpacity="0.1" />
    
    {/* Left Side (Stress) */}
    <g transform="translate(40, 60)">
      <circle r="25" fill="#ef4444" fillOpacity="0.2" />
      <path d="M-15 -5L-10 5L-5 -5L0 5L5 -5L10 5L15 -5" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M-20 20Q0 10 20 20" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
      <circle cx="-10" cy="-10" r="3" fill="#ef4444" />
      <circle cx="10" cy="-10" r="3" fill="#ef4444" />
    </g>

    {/* Divider */}
    <line x1="100" y1="20" x2="100" y2="100" stroke="white" strokeOpacity="0.1" strokeDasharray="4 4" />

    {/* Right Side (Calm) */}
    <g transform="translate(160, 60)">
      <circle r="25" fill="#10b981" fillOpacity="0.2" filter="url(#glow)" />
      <path d="M-15 10Q0 25 15 10" stroke="#10b981" strokeWidth="3" strokeLinecap="round" />
      <circle cx="-10" cy="-5" r="3" fill="#10b981" />
      <circle cx="10" cy="-5" r="3" fill="#10b981" />
      {/* Headphones */}
      <path d="M-28 0C-28 -15 -15 -28 0 -28C15 -28 28 -15 28 0V10" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
    </g>
  </svg>
);

export const IlluSpeedRun = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 120 120" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    <Defs />
    <g filter="url(#glow)">
      {/* Stopwatch Body */}
      <circle cx="60" cy="65" r="40" fill="url(#emeraldGrad)" stroke="white" strokeWidth="1" strokeOpacity="0.3" />
      <rect x="55" y="15" width="10" height="10" fill="#10b981" />
      <path d="M50 20L40 10M70 20L80 10" stroke="#10b981" strokeWidth="4" strokeLinecap="round" />
      
      {/* Face */}
      <circle cx="60" cy="65" r="32" fill="#064e3b" />
      <path d="M60 65L80 50" stroke="#34d399" strokeWidth="3" strokeLinecap="round" />
      
      {/* Motion Lines */}
      <path d="M10 65H20M15 50H25M15 80H25" stroke="#34d399" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
    </g>
  </svg>
);

export const IlluMoneySleep = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 150 100" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    <Defs />
    <g filter="url(#glow)">
      {/* Moon */}
      <circle cx="120" cy="20" r="12" fill="#fef3c7" fillOpacity="0.9" />
      
      {/* Chart Bars */}
      <rect x="20" y="60" width="20" height="30" rx="4" fill="#10b981" fillOpacity="0.4" />
      <rect x="50" y="45" width="20" height="45" rx="4" fill="#10b981" fillOpacity="0.6" />
      <rect x="80" y="25" width="20" height="65" rx="4" fill="#10b981" fillOpacity="0.9" />
      
      {/* Arrow Line */}
      <path d="M20 60L50 45L80 25L110 15" stroke="#34d399" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M105 15H110V20" stroke="#34d399" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      
      {/* Dollar Signs floating */}
      <text x="55" y="40" fill="#ecfccb" fontSize="10" fontWeight="bold">$</text>
      <text x="85" y="20" fill="#ecfccb" fontSize="12" fontWeight="bold">$</text>
    </g>
  </svg>
);
