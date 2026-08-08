import { motion } from "framer-motion";
import { Loader2, Send, User, Zap } from "lucide-react";
import React, { useEffect, useRef, useState } from "react";
import { sendMessageToBijou } from "../services/gemini";
import { track as trackPostHog } from "../services/posthog";

interface Message {
  role: "user" | "model";
  content: string;
}

interface DemoChatProps {
  onOpenModal: () => void;
}

export const DemoChat: React.FC<DemoChatProps> = ({ onOpenModal }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "model",
      content:
        "Eh hello boss! 👋 I'm Bijou, your AI Digital Employee. I reply customers 24/7, capture leads, book appointments — all in Manglish so they feel at home lah!\n\nFirst time we meet — nama you apa ah?",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isExcited, setIsExcited] = useState(false);
  const [showQuickReplies, setShowQuickReplies] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
    { icon: "�", text: "My name is Ahmad" },
    { icon: "🏠", text: "I'm a property agent" },
    { icon: "🍜", text: "I run an F&B business" },
    { icon: "💰", text: "What's the pricing?" },
    { icon: "📅", text: "I want to book a demo" },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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

    // Filter history for API context
    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    // PostHog: track demo chat turn
    trackPostHog("demo_chat_message_sent", {
      turn: messages.length + 1,
      is_quick_reply: Boolean(quickReplyText),
    });

    // Call Gemini API
    const responseText = await sendMessageToBijou(history, userMsg.content);

    setMessages((prev) => [...prev, { role: "model", content: responseText }]);
    setIsLoading(false);

    // PostHog: track demo chat response (without leaking message text)
    trackPostHog("demo_chat_response_received", {
      turn: messages.length + 1,
      response_length: responseText?.length || 0,
    });

    // Check for Manglish keywords to trigger animation
    const manglishKeywords =
      /walao|boss|can|settle|aiyo|fuyoh|best|swee|on|roger/i;
    if (manglishKeywords.test(responseText)) {
      setIsExcited(true);
      setTimeout(() => setIsExcited(false), 2000); // Glow for 2 seconds
    }
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
            Experience the "Manglish" difference. Try asking about pricing, or
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
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-black/30 to-black/50 scroll-smooth">
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

            <div ref={messagesEndRef} />
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
                Powered by Gemini. Bijou may display inaccurate info about
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
