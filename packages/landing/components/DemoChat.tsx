import { motion } from "framer-motion";
import { Calendar, Loader2, MessageCircle, Send, User, Zap } from "lucide-react";
import React, { useEffect, useRef, useState } from "react";
import { BookingContact, sendMessageToBijou } from "../services/gemini";
import { track as trackPostHog } from "../services/posthog";

interface Message {
  role: "user" | "model";
  content: string;
  booking?: BookingContact; // agent is ready to book → render the slot picker
}

const WHATSAPP_URL =
  "https://api.whatsapp.com/send/?phone=60174106981&text=" +
  encodeURIComponent("Hi Bijou! I was chatting with your AI demo on mybijou.xyz and would like to continue here.");

// Inline Cal.com slot picker (GET/POST /api/book). Native date input, no picker lib.
const SlotPicker: React.FC<{ contact: BookingContact; onBooked: (confirmation: string) => void }> = ({
  contact,
  onBooked,
}) => {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kuala_Lumpur";
  const today = new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD, local
  const [date, setDate] = useState(() => new Date(Date.now() + 86400000).toLocaleDateString("en-CA"));
  const [slots, setSlots] = useState<string[] | null>(null);
  const [bookingStart, setBookingStart] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setSlots(null);
    setError("");
    fetch(`/api/book?date=${date}&tz=${encodeURIComponent(tz)}`)
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        if (!d.ok) throw new Error(d.error);
        setSlots(d.slots);
      })
      .catch(() => !cancelled && setError("Aiyo, couldn't load the calendar. Try another date or WhatsApp us."));
    return () => {
      cancelled = true;
    };
  }, [date, tz]);

  const fmt = (iso: string, opts: Intl.DateTimeFormatOptions) =>
    new Date(iso).toLocaleString([], { timeZone: tz, ...opts });

  const book = async (start: string) => {
    setBookingStart(start);
    setError("");
    try {
      const r = await fetch("/api/book", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...contact, start, timeZone: tz, source: "demo_chat" }),
      });
      const d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error || "Booking failed");
      trackPostHog("cal_booking_completed", { source: "demo_chat" });
      onBooked(
        `You're booked for ${fmt(d.booking.start, { weekday: "long", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })} ✅\n\n` +
          `The calendar invite${d.booking.meetingUrl ? " and Google Meet link" : ""} is on its way to ${contact.email}.`,
      );
    } catch (e) {
      setError(`Couldn't book that slot (${(e as Error).message}). Please pick another time.`);
      setBookingStart(null);
    }
  };

  return (
    <div className="mt-4 pt-4 border-t border-white/10 space-y-3">
      <label className="flex items-center gap-2 text-sm text-emerald-300">
        <Calendar className="w-4 h-4" />
        <input
          type="date"
          value={date}
          min={today}
          onChange={(e) => e.target.value && setDate(e.target.value)}
          className="bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-white focus:outline-none focus:border-emerald-500/50 [color-scheme:dark]"
        />
        <span className="text-xs text-gray-400">{tz}</span>
      </label>
      {slots === null && !error && <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />}
      {slots?.length === 0 && <p className="text-sm text-gray-400">No free slots that day — try another date.</p>}
      {slots && slots.length > 0 && (
        <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto">
          {slots.map((s) => (
            <button
              key={s}
              disabled={bookingStart !== null}
              onClick={() => book(s)}
              className="px-3 py-1.5 bg-white/10 hover:bg-white/15 border border-emerald-500/20 rounded-full text-sm text-emerald-300 hover:text-emerald-200 transition-all disabled:opacity-50"
            >
              {bookingStart === s ? "Booking…" : fmt(s, { hour: "numeric", minute: "2-digit" })}
            </button>
          ))}
        </div>
      )}
      {error && <p className="text-sm text-amber-300">{error}</p>}
    </div>
  );
};

interface DemoChatProps {
  onOpenModal: () => void;
}

export const DemoChat: React.FC<DemoChatProps> = ({ onOpenModal }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "model",
      content:
        "Hi there! 👋 I'm Bijou, your AI Digital Employee. I reply to customers 24/7, capture leads, and book appointments — all in your brand voice.\n\nGreat to meet you — what's your name?",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isExcited, setIsExcited] = useState(false);
  const [showQuickReplies, setShowQuickReplies] = useState(true);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Signal Gem chat state machine
  const chatState: "idle" | "thinking" | "speaking" = isLoading
    ? "thinking"
    : isExcited
    ? "speaking"
    : "idle";

  // The Signal Gem mark (faceted gem with chat-bubble tail)
  const GemMark: React.FC<{ size?: number }> = ({ size = 48 }) => (
    <span
      className={`bj-gem state-${chatState}`}
      data-bj-state={chatState}
      style={{ width: size, height: size, display: "inline-block" }}
    >
      <span className="m" style={{ display: "block", width: size, height: size }}>
        <svg viewBox="0 0 100 100" width={size} height={size} aria-label="Bijou AI">
          <path
            className="gem-body"
            fill="#E3B457"
            d="M30,12 L70,12 L88,40 L70,73 L50,73 L26,92 L33,73 L12,40 Z"
          />
          <g
            className="bj-facets"
            fill="none"
            stroke="#0B3B2E"
            strokeWidth="1.6"
            strokeLinejoin="round"
            opacity="0.55"
          >
            <path className="facet-stroke" d="M40,26 L60,26 L68,40 L60,54 L40,54 L32,40 Z" />
            <path className="facet-stroke" d="M50,26 L50,54" />
            <path className="facet-stroke" d="M40,26 L30,12 M60,26 L70,12" />
            <path className="facet-stroke" d="M32,40 L12,40 M68,40 L88,40" />
            <path className="facet-stroke" d="M40,54 L30,73 M60,54 L70,73" />
          </g>
        </svg>
      </span>
    </span>
  );

  const quickReplies = [
    { icon: "👋", text: "My name is Alex" },
    { icon: "🏠", text: "I'm a property agent" },
    { icon: "🍜", text: "I run an F&B business" },
    { icon: "💰", text: "What's the pricing?" },
    { icon: "📅", text: "I want to book a demo" },
  ];

  // Scroll only the chat's own message list. scrollIntoView() also scrolls the
  // page, which yanked visitors down to the chat on load and on every message.
  const scrollToBottom = () => {
    const el = messagesContainerRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleQuickReply = (text: string) => {
    setInputValue(text);
    setShowQuickReplies(false);
    // Auto-send the message
    setTimeout(() => handleSend(text), 100);
  };

  const handleSend = async (quickReplyText?: string) => {
    const messageText = quickReplyText || inputValue;
    if (!messageText.trim() || isLoading) return;

    const userMsg: Message = { role: "user", content: messageText };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsLoading(true);
    setShowQuickReplies(false);

    // Signal Gem: soft "sent" tick on user send. The visual `state-thinking`
    // is driven by React's isLoading, and the audio controller's
    // MutationObserver picks up the data-bj-state flip and syncs setState.
    try {
      const w = window as unknown as { BjAudio?: { tick?: () => void } };
      w.BjAudio && w.BjAudio.tick && w.BjAudio.tick();
    } catch (_) { /* BjAudio not loaded yet */ }

    // Filter history for API context
    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    // PostHog: track demo chat turn
    trackPostHog("demo_chat_message_sent", {
      turn: messages.length + 1,
      is_quick_reply: Boolean(quickReplyText),
    });

    // Call Gemini API
    const { text: responseText, booking } = await sendMessageToBijou(history, userMsg.content);

    setMessages((prev) => [...prev, { role: "model", content: responseText, booking }]);
    setIsLoading(false);

    // Signal Gem: trigger the excited glow + speaking pulse (which
    // drives state-speaking via chatState derivation). The data-bj-state
    // change is auto-detected by the audio controller's MutationObserver
    // and broadcasts to all gems on the page.
    // Check for upbeat keywords to trigger the excited-glow animation
    const excitedKeywords =
      /great|perfect|absolutely|done|confirmed|awesome|happy to|let's/i;
    if (excitedKeywords.test(responseText)) {
      setIsExcited(true);
      setTimeout(() => setIsExcited(false), 2000); // Glow for 2 seconds
    }

    // PostHog: track demo chat response (without leaking message text)
    trackPostHog("demo_chat_response_received", {
      turn: messages.length + 1,
      response_length: responseText?.length || 0,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <section id="demo" className="py-24 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-t from-dark-900 to-transparent pointer-events-none" />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <div className="inline-block px-4 py-1.5 mb-6 rounded-full glass-panel-3d border border-emerald-500/20 text-emerald-400 text-sm font-bold tracking-wider shadow-[0_0_20px_rgba(16,185,129,0.15)]">
            LIVE PREVIEW
          </div>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Talk to Bijou</h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Experience the done-for-you difference. Try asking about pricing, or
            try to book a slot.
          </p>
        </motion.div>

        <div className="glass-panel-3d rounded-3xl overflow-hidden shadow-2xl flex flex-col h-[700px] border border-white/10 relative ring-1 ring-white/5">
          {/* Chat Header */}
          <div className="bg-white/5 border-b border-white/5 p-6 flex items-center gap-4 backdrop-blur-md">
            <div className="relative">
              <div
                className="w-12 h-12 flex items-center justify-center z-10 relative"
                style={{ filter: "drop-shadow(0 0 12px rgba(227, 180, 87, 0.4))" }}
              >
                <GemMark size={48} />
              </div>
              <div className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-green-400 rounded-full border-2 border-gray-800 z-20 shadow-md"></div>
            </div>
            <div>
              <div className="font-bold text-white text-lg">
                Bijou Digital Employee
              </div>
              <div className="text-xs text-emerald-400 flex items-center gap-1.5 font-medium tracking-wide mt-0.5">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse shadow-[0_0_5px_#34d399]"></span>
                Online • Replies Instantly
              </div>
            </div>
            <a
              href={WHATSAPP_URL}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => trackPostHog("whatsapp_cta_clicked", { source: "demo_chat" })}
              className="ml-auto inline-flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-dark-900 rounded-full text-sm font-bold transition-colors shadow-[0_0_15px_rgba(16,185,129,0.3)]"
            >
              <MessageCircle className="w-4 h-4" />
              <span className="hidden sm:inline">Continue on WhatsApp</span>
              <span className="sm:hidden">WhatsApp</span>
            </a>
          </div>

          {/* Chat Messages */}
          <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-black/30 to-black/50 scroll-smooth">
            {messages.map((msg, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.3 }}
                className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
              >
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg ${msg.role === "user" ? "bg-gray-700" : "bg-transparent"}`}
                >
                  {msg.role === "user" ? (
                    <User className="w-5 h-5 text-gray-300" />
                  ) : (
                    <GemMark size={40} />
                  )}
                </div>
                <div
                  className={`rounded-2xl p-5 max-w-[80%] shadow-lg ${
                    msg.role === "user"
                      ? "glossy-pill rounded-tr-none text-white"
                      : "glossy-pill-emerald rounded-tl-none text-emerald-50"
                  }`}
                >
                  <p className="text-base leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </p>
                  {msg.booking && (
                    <SlotPicker
                      contact={msg.booking}
                      onBooked={(confirmation) =>
                        setMessages((prev) => [
                          ...prev.map((m, i) => (i === idx ? { ...m, booking: undefined } : m)),
                          { role: "model", content: confirmation },
                        ])
                      }
                    />
                  )}
                </div>
              </motion.div>
            ))}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-4"
              >
                <div className="w-10 h-10 rounded-full bg-transparent flex items-center justify-center flex-shrink-0 shadow-lg">
                  <GemMark size={40} />
                </div>
                <div className="glossy-pill-emerald p-5 rounded-2xl rounded-tl-none flex items-center gap-3 shadow-lg">
                  <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
                  <span className="text-sm text-emerald-400 font-medium">
                    Bijou is typing...
                  </span>
                </div>
              </motion.div>
            )}

            {/* Quick Reply Chips */}
            {showQuickReplies && messages.length === 1 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="flex flex-wrap gap-2 px-2"
              >
                {quickReplies.map((reply, idx) => (
                  <motion.button
                    key={idx}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.7 + idx * 0.1 }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleQuickReply(reply.text)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/15 border border-emerald-500/20 rounded-full text-sm text-emerald-300 hover:text-emerald-200 transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-emerald-500/10"
                  >
                    <span>{reply.icon}</span>
                    <span>{reply.text}</span>
                  </motion.button>
                ))}
              </motion.div>
            )}

          </div>

          {/* Input Area */}
          <div className="p-6 bg-white/5 border-t border-white/5 backdrop-blur-xl">
            <div className="relative">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message (e.g. 'How much?', 'Can help with my dental clinic?')"
                className="w-full bg-black/40 border border-white/10 rounded-xl pl-6 pr-14 py-5 text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all shadow-inner text-base"
              />
              <button
                onClick={() => handleSend()}
                disabled={isLoading || !inputValue.trim()}
                className="absolute right-2.5 top-2.5 p-2.5 bg-emerald-500 hover:bg-emerald-400 text-dark-900 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:shadow-[0_0_20px_rgba(16,185,129,0.5)]"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            <div className="text-center mt-4 space-y-2">
              <p className="text-xs text-gray-500 flex items-center justify-center gap-2">
                <Zap className="w-3 h-3 text-emerald-500" />
                AI-generated replies. Bijou may display inaccurate info about
                people or places.
              </p>
              <p className="text-xs text-gray-400">
                Want to chat with a human instead?{" "}
                <a
                  href="https://wa.me/60174106981?text=Hi%20Bijou%2C%20I%27d%20like%20to%20try%20a%20demo"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 hover:text-emerald-300 transition-colors underline"
                >
                  WhatsApp us
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
