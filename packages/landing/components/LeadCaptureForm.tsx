import { AnimatePresence, motion } from "framer-motion";
import {
    AlertCircle,
    ArrowRight,
    Building2,
    CheckCircle,
    Mail,
    Phone,
    User,
} from "lucide-react";
import React, { useState } from "react";
import { track, identifyUser } from "../services/posthog";

interface LeadCaptureFormProps {
  source: string;
  className?: string;
  onSuccess?: (leadData: any) => void;
}

const INDUSTRIES = [
  { value: "real_estate", label: "Real Estate" },
  { value: "insurance", label: "Insurance" },
  { value: "automotive", label: "Automotive" },
  { value: "retail", label: "Retail & E-commerce" },
  { value: "hospitality", label: "Hospitality & Tourism" },
  { value: "financial", label: "Financial Services" },
  { value: "healthcare", label: "Healthcare" },
  { value: "education", label: "Education" },
  { value: "technology", label: "Technology" },
  { value: "other", label: "Other" },
];

export const LeadCaptureForm: React.FC<LeadCaptureFormProps> = ({
  source = "hero_form",
  className = "",
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    company: "",
    industry: "",
  });

  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [marketingConsent, setMarketingConsent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");

    // Client-side validation
    if (!formData.name.trim() || !formData.email.trim()) {
      setStatus("error");
      setErrorMessage("Name and email are required");
      return;
    }

    // Email validation. Allows `+` in the local part (e.g. john+test@gmail.com),
    // requires a 2+ char TLD. Matches the pattern in api/leads.js.
    const emailRegex = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;
    if (!emailRegex.test(formData.email)) {
      setStatus("error");
      setErrorMessage("Please enter a valid email address");
      return;
    }

    try {
      const leadPayload = {
        name: formData.name.trim(),
        email: formData.email.toLowerCase().trim(),
        phone: formData.phone || "",
        company: formData.company || "",
        industry: formData.industry || "",
        source: source,
        marketing_consent: marketingConsent,
      };

      // PostHog: capture the submit attempt (with the industry source).
      track("lead_capture_form_submitted", {
        source,
        industry: formData.industry || undefined,
        has_company: Boolean(formData.company),
        has_phone: Boolean(formData.phone),
        marketing_consent: marketingConsent,
      });

      const response = await fetch("/api/leads", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(leadPayload),
      });

      const result = await response.json();

      if (!response.ok) {
        track("lead_capture_form_failed", {
          source,
          status: response.status,
        });
        if (result.detail?.[0]?.msg) {
          throw new Error(result.detail[0].msg);
        }
        throw new Error(result.message || "Failed to submit form");
      }

      // PostHog: identify the user now that we have a known email, and
      // mark the conversion. Server-side captureServer will run as a
      // backstop from api/leads.js.
      identifyUser(formData.email.toLowerCase().trim(), {
        email: formData.email.toLowerCase().trim(),
        name: formData.name.trim(),
        company: formData.company || undefined,
        industry: formData.industry || undefined,
        source,
        created_at: new Date().toISOString(),
      });
      track("signup_modal_completed", {
        source,
        industry: formData.industry || undefined,
      });

      setStatus("success");

      // Call success callback if provided
      if (onSuccess) {
        onSuccess(result);
      }

      // Reset form after delay
      setTimeout(() => {
        setFormData({
          name: "",
          email: "",
          phone: "",
          company: "",
          industry: "",
        });
        setMarketingConsent(false);
        setStatus("idle");
      }, 5000);
    } catch (error: any) {
      setStatus("error");
      if (
        error.message.includes("duplicate") ||
        error.message.includes("already")
      ) {
        setErrorMessage(
          "Already registered! Check your email for the onboarding link.",
        );
      } else {
        setErrorMessage(
          error.message || "Aiyo, something went wrong boss. Please try again.",
        );
      }
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (status === "error") {
      setStatus("idle");
      setErrorMessage("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className={`space-y-6 ${className}`}>
      <AnimatePresence>
        {status === "success" && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="flex items-center gap-3 p-4 rounded-xl glass-panel-3d border-emerald-500/30 bg-emerald-500/10"
          >
            <CheckCircle className="w-6 h-6 text-emerald-400 flex-shrink-0" />
            <div>
              <p className="text-emerald-400 font-semibold">
                Swee! Got your details, boss!
              </p>
              <p className="text-emerald-300 text-sm">
                Check your email — we've sent a confirmation with your
                onboarding link.
              </p>
            </div>
          </motion.div>
        )}

        {status === "error" && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="flex items-center gap-3 p-4 rounded-xl glass-panel-3d border-red-500/30 bg-red-500/10"
          >
            <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
            <div>
              <p className="text-red-400 font-semibold">
                Aiyo, something went wrong
              </p>
              <p className="text-red-300 text-sm">{errorMessage}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="relative">
          <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Your name *"
            value={formData.name}
            onChange={(e) => handleInputChange("name", e.target.value)}
            className="w-full pl-12 pr-4 py-4 rounded-xl glass-panel-3d border border-white/10 focus:border-emerald-500/50 focus:outline-none text-white placeholder-gray-400 text-lg transition-all"
            required
          />
        </div>

        <div className="relative">
          <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="email"
            placeholder="Email address *"
            value={formData.email}
            onChange={(e) => handleInputChange("email", e.target.value)}
            className="w-full pl-12 pr-4 py-4 rounded-xl glass-panel-3d border border-white/10 focus:border-emerald-500/50 focus:outline-none text-white placeholder-gray-400 text-lg transition-all"
            required
          />
        </div>

        <div className="relative">
          <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="tel"
            placeholder="Phone number"
            value={formData.phone}
            onChange={(e) => handleInputChange("phone", e.target.value)}
            className="w-full pl-12 pr-4 py-4 rounded-xl glass-panel-3d border border-white/10 focus:border-emerald-500/50 focus:outline-none text-white placeholder-gray-400 text-lg transition-all"
          />
        </div>

        <div className="relative">
          <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Company name"
            value={formData.company}
            onChange={(e) => handleInputChange("company", e.target.value)}
            className="w-full pl-12 pr-4 py-4 rounded-xl glass-panel-3d border border-white/10 focus:border-emerald-500/50 focus:outline-none text-white placeholder-gray-400 text-lg transition-all"
          />
        </div>
      </div>

      <div className="relative">
        <Building2 className="absolute left-3 top-6 w-5 h-5 text-gray-400" />
        <select
          value={formData.industry}
          onChange={(e) => handleInputChange("industry", e.target.value)}
          className="w-full pl-12 pr-4 py-4 rounded-xl glass-panel-3d border border-white/10 focus:border-emerald-500/50 focus:outline-none text-white text-lg transition-all appearance-none bg-transparent"
        >
          <option value="" className="bg-gray-800 text-white">
            Select your industry
          </option>
          {INDUSTRIES.map((industry) => (
            <option
              key={industry.value}
              value={industry.value}
              className="bg-gray-800 text-white"
            >
              {industry.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          id="marketing-consent"
          checked={marketingConsent}
          onChange={(e) => setMarketingConsent(e.target.checked)}
          className="mt-1 w-4 h-4 text-emerald-500 bg-transparent border border-white/30 rounded focus:ring-emerald-500 focus:ring-2"
        />
        <label
          htmlFor="marketing-consent"
          className="text-sm text-gray-300 leading-relaxed"
        >
          I want to receive updates about Bijou AI, exclusive tips for Malaysian
          SMEs, and special offers. You can unsubscribe anytime with one click.
        </label>
      </div>

      <motion.button
        type="submit"
        disabled={status === "loading"}
        whileHover={status !== "loading" ? { scale: 1.02 } : {}}
        whileTap={status !== "loading" ? { scale: 0.98 } : {}}
        className={`w-full flex items-center justify-center gap-3 py-5 px-8 rounded-xl font-bold text-lg transition-all ${
          status === "loading"
            ? "bg-gray-600 text-gray-300 cursor-not-allowed"
            : "bg-gradient-to-r from-emerald-500 to-emerald-400 text-dark-900 shadow-[0_0_30px_rgba(16,185,129,0.4)] hover:shadow-[0_0_50px_rgba(16,185,129,0.6)]"
        }`}
      >
        {status === "loading" ? (
          <>
            <div className="w-5 h-5 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
            Processing...
          </>
        ) : (
          <>
            Get My Free Demo
            <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
          </>
        )}
      </motion.button>

      <p className="text-xs text-gray-400 text-center leading-relaxed">
        By submitting this form, you agree to our{" "}
        <a
          href="/privacy"
          className="text-emerald-400 hover:text-emerald-300 transition-colors"
        >
          Privacy Policy
        </a>{" "}
        and consent to being contacted by our team. PDPA compliant.
      </p>
    </form>
  );
};
