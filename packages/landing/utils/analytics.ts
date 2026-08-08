/**
 * Google Analytics 4 + PostHog tracking utilities for Bijou AI
 *
 * Each helper fires to GA4 (existing) AND PostHog (new) so the existing
 * call sites get both for free. PostHog is gated behind an import so that
 * the bundle stays small when the project key is not configured.
 *
 * Usage: Import tracking functions and call them when user actions occur
 * All events include user_language parameter for A/B testing
 */

import { track as trackPostHog } from "../services/posthog";

// Type definition for gtag function (global from index.html)
declare global {
  interface Window {
    gtag: (
      command: string,
      eventName: string,
      params?: Record<string, any>
    ) => void;
  }
}

/**
 * Track language switch events
 * Use case: Measure which languages users prefer
 *
 * @param language - ISO 639-1 language code (en, ms, zh, ta)
 */
export const trackLanguageChange = (language: string): void => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', 'language_change', {
      user_language: language,
      event_category: 'engagement',
      event_label: `switched_to_${language}`
    });
  }
  trackPostHog("language_change", { user_language: language });
};

/**
 * Track trial signup button clicks
 * Use case: Measure conversion intent by language
 *
 * @param language - Current selected language when CTA clicked
 */
export const trackTrialSignup = (language: string): void => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', 'trial_signup_click', {
      user_language: language,
      event_category: 'conversion',
      event_label: 'start_free_trial_cta',
      value: 1
    });
  }
  trackPostHog("hero_cta_clicked", {
    cta: 'start_free_trial',
    user_language: language,
  });
};

/**
 * Track demo booking button clicks
 * Use case: Measure enterprise interest by language
 *
 * @param language - Current selected language when CTA clicked
 */
export const trackDemoBooking = (language: string): void => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', 'demo_booking_click', {
      user_language: language,
      event_category: 'conversion',
      event_label: 'book_demo_cta',
      value: 2
    });
  }
  trackPostHog("cal_booking_opened", {
    user_language: language,
    cta: 'book_demo_hero',
  });
};

/**
 * Track form submission events
 * Use case: Measure lead generation by form type and language
 *
 * @param formType - Type of form submitted (enterprise, partnership, integration)
 * @param language - Current selected language when form submitted
 */
export const trackFormSubmission = (formType: string, language: string): void => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', 'form_submission', {
      user_language: language,
      event_category: 'lead_generation',
      event_label: `${formType}_form`,
      form_type: formType,
      value: 5
    });
  }
  trackPostHog("lead_capture_form_submitted", {
    form_type: formType,
    user_language: language,
  });
};

/**
 * Track pricing plan selection (optional - for future use)
 * Use case: Measure which plans are most popular by language
 *
 * @param planName - Name of pricing plan (starter, professional, enterprise)
 * @param language - Current selected language
 */
export const trackPlanSelection = (planName: string, language: string): void => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', 'plan_selection', {
      user_language: language,
      event_category: 'engagement',
      event_label: `${planName}_plan`,
      plan_name: planName
    });
  }
  trackPostHog("pricing_plan_clicked", {
    plan_name: planName,
    user_language: language,
  });
};
