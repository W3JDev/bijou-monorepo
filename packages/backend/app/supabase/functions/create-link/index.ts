// Supabase Edge Function — create-link
//
// SECURITY (2026-07-20): This function was previously unauthenticated, allowing
// anyone to store arbitrary destination URLs in `short_links` (then served
// under the `mybijou.xyz/l/<slug>` domain). Now requires:
//   - `X-Internal-Token` header matching the `INTERNAL_API_TOKEN` env var.
//   - The constructed `destination_url` MUST be a `wa.me` or
//     `api.whatsapp.com` URL — we whitelist the host.
//
// See audit-report.md findings #3 and #5.

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { nanoid } from 'https://esm.sh/nanoid@4'

declare const Deno: any;

const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://mybijou.xyz',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-internal-token',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

const ALLOWED_HOSTS = new Set(['wa.me', 'www.wa.me', 'api.whatsapp.com'])

function isAllowedWhatsappUrl(raw: string): boolean {
  try {
    const u = new URL(raw)
    return ALLOWED_HOSTS.has(u.hostname.toLowerCase())
  } catch {
    return false
  }
}

Deno.serve(async (req: any) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }
  if (req.method !== 'POST') {
    return new Response('Method not allowed', { status: 405, headers: corsHeaders })
  }

  // Internal-only auth.
  const expected = Deno.env.get('INTERNAL_API_TOKEN')
  if (!expected) {
    return new Response(
      JSON.stringify({ error: 'misconfigured' }),
      { status: 503, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    )
  }
  if (req.headers.get('x-internal-token') !== expected) {
    return new Response(
      JSON.stringify({ error: 'unauthorized' }),
      { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    )
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    )

    const { phone, message, email } = await req.json()
    if (!phone) throw new Error('Phone number is required')

    // 1. Construct standard WhatsApp URL
    const cleanPhone = String(phone).replace(/\D/g, '')
    if (cleanPhone.length < 8 || cleanPhone.length > 20) {
      throw new Error('Phone number out of range')
    }
    const longUrl = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(message || '')}`

    // 2. Validate the constructed URL is a wa.me URL (defense-in-depth).
    if (!isAllowedWhatsappUrl(longUrl)) {
      throw new Error('Constructed URL failed allowlist check')
    }

    // 3. Generate a unique short slug (5 chars)
    const slug = nanoid(5)

    // 4. Save to Database
    const { data, error } = await supabase
      .from('short_links')
      .insert([
        { slug, destination_url: longUrl, owner_email: email || null },
      ])
      .select()
      .single()

    if (error) throw error

    return new Response(
      JSON.stringify({
        shortLink: `https://mybijou.xyz/l/${slug}`,
        originalUrl: longUrl,
        trackingId: data.id,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    )
  } catch (error: any) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 400,
    })
  }
})
