-- BIJOU AI LEADS TABLE - Enhanced Safety Version
-- This version uses tenant-specific naming to match your schema patterns

-- 1. Create the leads table
CREATE TABLE IF NOT EXISTS public.leads (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  
  -- Lead Information
  name text NOT NULL,
  email text NOT NULL,
  phone text,
  company text,
  industry text,
  
  -- Lead Source & Context  
  source text NOT NULL DEFAULT 'website', -- 'hero_form', 'cal_booking', 'waitlist', 'whatsapp_cta', 'final_cta_direct'
  utm_source text,
  utm_medium text,
  utm_campaign text,
  referrer text,
  
  -- Lead Status & Qualification
  status text NOT NULL DEFAULT 'new', -- 'new', 'contacted', 'qualified', 'customer', 'lost'
  lead_score int DEFAULT 0,
  notes text,
  
  -- Privacy & Compliance (PDPA for Malaysian market)
  marketing_consent boolean DEFAULT false,
  pdpa_consent boolean DEFAULT true,
  
  -- Analytics & Device Detection
  ip_address inet,
  user_agent text,
  device_type text,
  location_country text,
  location_city text,
  
  -- Email Engagement Tracking
  email_sent_at timestamp with time zone,
  email_opened_at timestamp with time zone,  
  email_clicked_at timestamp with time zone,
  
  -- Data Validation Constraints
  CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$'),
  CONSTRAINT valid_status CHECK (status IN ('new', 'contacted', 'qualified', 'customer', 'lost')),
  CONSTRAINT valid_source CHECK (source IN ('hero_form', 'cal_booking', 'waitlist', 'whatsapp_cta', 'website', 'referral', 'final_cta_direct'))
);

-- 2. Create performance indexes
CREATE INDEX IF NOT EXISTS idx_leads_email ON public.leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_status ON public.leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_source ON public.leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON public.leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_updated_at ON public.leads(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_lead_score ON public.leads(lead_score DESC);

-- 3. Enable Row Level Security
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

-- 4. Create RLS policies for API access
DROP POLICY IF EXISTS "Enable full access for service role" ON public.leads;
CREATE POLICY "Enable full access for service role" ON public.leads
  FOR ALL USING (auth.role() = 'service_role');

-- 5. ENHANCED: Leads-specific update function (matches your naming patterns)
CREATE OR REPLACE FUNCTION public.update_leads_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = timezone('utc'::text, now());
  RETURN NEW;
END;
$$ language plpgsql;

-- 6. Create trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS update_leads_updated_at ON public.leads;
CREATE TRIGGER update_leads_updated_at
  BEFORE UPDATE ON public.leads
  FOR EACH ROW
  EXECUTE FUNCTION public.update_leads_updated_at_column();

-- 7. Lead scoring business logic function  
CREATE OR REPLACE FUNCTION public.calculate_lead_score(lead_data public.leads)
RETURNS int AS $$
DECLARE
  score int := 0;
BEGIN
  -- Base score for complete profile
  IF lead_data.name IS NOT NULL AND lead_data.email IS NOT NULL THEN
    score := score + 10;
  END IF;
  
  -- Phone number adds significant value
  IF lead_data.phone IS NOT NULL AND length(lead_data.phone) > 8 THEN
    score := score + 15;
  END IF;
  
  -- Company information shows business intent
  IF lead_data.company IS NOT NULL AND length(lead_data.company) > 2 THEN
    score := score + 20;
  END IF;
  
  -- Industry context helps with qualification
  IF lead_data.industry IS NOT NULL THEN
    score := score + 10;
  END IF;
  
  -- Email engagement tracking
  IF lead_data.email_opened_at IS NOT NULL THEN
    score := score + 25;
  END IF;
  
  IF lead_data.email_clicked_at IS NOT NULL THEN
    score := score + 35;
  END IF;
  
  -- Marketing consent shows higher intent
  IF lead_data.marketing_consent = true THEN
    score := score + 15;
  END IF;
  
  -- Source-based scoring (Malaysian market behavior)
  CASE lead_data.source
    WHEN 'cal_booking' THEN score := score + 50;      -- Booked demo = highest intent
    WHEN 'whatsapp_cta' THEN score := score + 40;     -- Direct WhatsApp = high intent  
    WHEN 'final_cta_direct' THEN score := score + 35; -- Bottom CTA = high intent
    WHEN 'hero_form' THEN score := score + 30;        -- Main form = medium-high intent
    WHEN 'waitlist' THEN score := score + 20;         -- Email signup = medium intent
    ELSE score := score + 10;                          -- Other sources = baseline
  END CASE;
  
  RETURN score;
END;
$$ language plpgsql;

-- 8. Optional: Add sample data validation (remove after testing)
-- INSERT INTO public.leads (name, email, source, marketing_consent) 
-- VALUES ('Test User', 'test@mybijou.xyz', 'hero_form', true);

-- 9. Verification query (run this after to confirm setup)
-- SELECT 
--   id, name, email, source, lead_score, created_at 
-- FROM public.leads 
-- ORDER BY created_at DESC 
-- LIMIT 5;

-- ✅ SETUP COMPLETE
-- This creates a production-ready leads table with:
-- • PDPA compliance for Malaysian market
-- • Advanced lead scoring algorithm  
-- • Email engagement tracking
-- • Source attribution for conversion analysis
-- • Row-level security for API access
-- • Performance-optimized indexes