-- BIJOU AI LEADS TABLE - Missing table creation
-- Run this in your Supabase SQL Editor to add the leads table

-- 1. Create the leads table (the missing piece)
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
  
  -- Privacy & Compliance
  marketing_consent boolean DEFAULT false,
  pdpa_consent boolean DEFAULT true,
  
  -- Analytics
  ip_address inet,
  user_agent text,
  device_type text,
  location_country text,
  location_city text,
  
  -- Email Integration
  email_sent_at timestamp with time zone,
  email_opened_at timestamp with time zone,
  email_clicked_at timestamp with time zone,
  
  -- Constraints
  CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$'),
  CONSTRAINT valid_status CHECK (status IN ('new', 'contacted', 'qualified', 'customer', 'lost')),
  CONSTRAINT valid_source CHECK (source IN ('hero_form', 'cal_booking', 'waitlist', 'whatsapp_cta', 'website', 'referral', 'final_cta_direct'))
);

-- 2. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_leads_email ON public.leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_status ON public.leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_source ON public.leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON public.leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_updated_at ON public.leads(updated_at DESC);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

-- 4. Create a policy for service role (for API access)
DROP POLICY IF EXISTS "Enable full access for service role" ON public.leads;
CREATE POLICY "Enable full access for service role" ON public.leads
  FOR ALL USING (auth.role() = 'service_role');

-- 5. Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = timezone('utc'::text, now());
  RETURN NEW;
END;
$$ language plpgsql;

-- 6. Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_leads_updated_at ON public.leads;
CREATE TRIGGER update_leads_updated_at
  BEFORE UPDATE ON public.leads
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- 7. Function to calculate lead score (business logic)
CREATE OR REPLACE FUNCTION calculate_lead_score(lead_data public.leads)
RETURNS int AS $$
DECLARE
  score int := 0;
BEGIN
  -- Base score for complete profile
  IF lead_data.name IS NOT NULL AND lead_data.email IS NOT NULL THEN
    score := score + 10;
  END IF;
  
  -- Phone number adds value
  IF lead_data.phone IS NOT NULL AND length(lead_data.phone) > 8 THEN
    score := score + 15;
  END IF;
  
  -- Company information valuable
  IF lead_data.company IS NOT NULL AND length(lead_data.company) > 2 THEN
    score := score + 20;
  END IF;
  
  -- Industry context
  IF lead_data.industry IS NOT NULL THEN
    score := score + 10;
  END IF;
  
  -- Email engagement
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
  
  -- High-value sources
  IF lead_data.source = 'cal_booking' THEN
    score := score + 50;  -- Booked a demo = high intent
  ELSIF lead_data.source = 'hero_form' THEN
    score := score + 30;  -- Main CTA = medium-high intent  
  ELSIF lead_data.source = 'whatsapp_cta' THEN
    score := score + 40;  -- Direct contact = high intent
  ELSIF lead_data.source = 'final_cta_direct' THEN
    score := score + 35;  -- Direct trial signup = high intent
  END IF;
  
  RETURN score;
END;
$$ language plpgsql;

-- 8. Test the setup (optional)
-- INSERT INTO public.leads (name, email, source) VALUES ('Test User', 'test@example.com', 'hero_form');
-- SELECT * FROM public.leads WHERE email = 'test@example.com';