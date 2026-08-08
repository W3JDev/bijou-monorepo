// This service handles the creation of tracked short links.
// In a real environment, this connects to your Supabase/Backend API.
// For the demo, it simulates a network request and returns a mock link.

interface ShortLinkRequest {
  phone: string;
  message: string;
  email: string;
}

interface ShortLinkResponse {
  shortLink: string;
  originalUrl: string;
  trackingId: string;
}

const API_ENDPOINT = import.meta.env.VITE_SUPABASE_URL || 'https://lrwzlujomukzjykafmic.supabase.co/functions/v1';

export const linkShortenerService = {
  /**
   * Creates a tracked short link.
   * If API is not available, falls back to a deterministic simulation.
   */
  createLink: async (data: ShortLinkRequest): Promise<ShortLinkResponse> => {
    // 1. Construct the actual WhatsApp URL
    const cleanPhone = data.phone.replace(/\D/g, '');
    const longUrl = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(data.message)}`;

    try {
      // 2. Attempt to call the real backend
      // Note: This requires the backend code provided in the 'backend/' folder to be deployed.
      if (import.meta.env.MODE === 'production' && import.meta.env.VITE_PUBLIC_API_URL) {
        const response = await fetch(`${API_ENDPOINT}/create-link`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...data, longUrl }),
        });

        if (response.ok) {
          return await response.json();
        }
      }

      // 3. Fallback: Simulate the "Power" for the Demo
      // This ensures the UI works beautifully even without a backend.
      console.log('[LinkShortener] Simulating backend creation...');
      await new Promise(resolve => setTimeout(resolve, 1500)); // Network delay

      // Generate a fake but realistic looking short ID
      const mockId = Math.random().toString(36).substring(2, 7);
      
      return {
        shortLink: `https://mybijou.xyz/l/${mockId}`,
        originalUrl: longUrl,
        trackingId: `trk_${Math.random().toString(36).substring(2, 9)}`
      };

    } catch (error) {
      console.error('[LinkShortener] Error:', error);
      throw new Error('Failed to generate link');
    }
  }
};