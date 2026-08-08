import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// SECURITY (2026-07-20):
//   - loadEnv is called with the empty prefix (third arg '') so we can
//     read BOTH VITE_* and non-VITE_ vars. Only `VITE_PUBLIC_SITE_URL`
//     is exposed via `define` — that is the ONLY env var that ends up
//     in the client bundle. All other env vars (Gemini, Supabase, Resend,
//     Stripe, INTERNAL_API_TOKEN) are server-only because they are never
//     referenced from the `define` block and because Vite does not
//     auto-expose non-VITE_* vars to the browser.
//   - Vite automatically sets `process.env.NODE_ENV` from `mode`; the
//     redundant define was removed.
//   - See audit-report.md finding #9 for the VITE_GEMINI_API_KEY footgun
//     (the prefix is misleading; rename in a follow-up).
export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
      },
      plugins: [react()],
      define: {
        'process.env.VITE_PUBLIC_SITE_URL': JSON.stringify(env.VITE_PUBLIC_SITE_URL || 'https://mybijou.xyz')
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
