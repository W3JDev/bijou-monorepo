// Supabase Edge Function — redirect
//
// SECURITY (2026-07-20): Was previously a wide-open redirect. Any URL stored
// in `short_links.destination_url` was blindly followed. Now validates that
// the destination is on a `wa.me` allowlist before redirecting. This closes
// the open-redirect / phishing-as-a-service vector on the mybijou.xyz
// short-link domain.
// See audit-report.md finding #3.

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

declare const Deno: any;

const ALLOWED_HOSTS = new Set(['wa.me', 'www.wa.me', 'api.whatsapp.com'])

function isAllowedRedirectUrl(raw: string | null | undefined): boolean {
  if (!raw) return false
  try {
    const u = new URL(raw)
    if (u.protocol !== 'https:') return false
    return ALLOWED_HOSTS.has(u.hostname.toLowerCase())
  } catch {
    return false
  }
}

Deno.serve(async (req: any) => {
  const url = new URL(req.url)
  // Assumes URL pattern: https://project.supabase.co/functions/v1/redirect?slug=xyz
  // Or proxied via: https://bijou.ai/l/xyz
  const slug = url.searchParams.get('slug') ?? url.pathname.split('/').pop()

  if (!slug) {
    return new Response('Not Found', {
      status: 404,
      headers: { 'X-Content-Type-Options': 'nosniff' },
    })
  }

  // Basic slug format check — nanoid() generates [A-Za-z0-9_-] chars.
  if (!/^[A-Za-z0-9_-]{1,32}$/.test(slug)) {
    return new Response('Not Found', {
      status: 404,
      headers: { 'X-Content-Type-Options': 'nosniff' },
    })
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
  )

  // 1. Find the link
  const { data: link } = await supabase
    .from('short_links')
    .select('id, destination_url')
    .eq('slug', slug)
    .single()

  if (!link) {
    return new Response('Link not found', {
      status: 404,
      headers: { 'X-Content-Type-Options': 'nosniff' },
    })
  }

  // 2. SECURITY: Validate destination URL is on the wa.me allowlist.
  // If a legacy row has a non-allowlist URL, we refuse to redirect rather
  // than following it. Operators should run a one-time cleanup migration
  // to delete any non-conforming rows.
  if (!isAllowedRedirectUrl(link.destination_url)) {
    console.warn(
      `Blocked redirect for slug=${slug}: non-allowlist destination ${link.destination_url}`,
    )
    return new Response('Link unavailable', {
      status: 410, // Gone
      headers: { 'X-Content-Type-Options': 'nosniff' },
    })
  }

  // 3. Log analytics (async, do not await — speed up the redirect).
  const userAgent = req.headers.get('user-agent')
  const ip = req.headers.get('x-forwarded-for')

  try {
    await supabase.rpc('increment_click_count', { row_id: link.id })
  } catch {
    // Non-fatal: analytics is best-effort.
  }
  try {
    await supabase.from('link_clicks').insert({
      link_id: link.id,
      user_agent: userAgent,
      ip_address: ip,
    })
  } catch {
    // Non-fatal.
  }

  // 4. Redirect User (validated destination).
  return Response.redirect(link.destination_url, 301)
})
