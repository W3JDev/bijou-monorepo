// Present when the agent is ready to book: prefills the inline slot picker.
export interface BookingContact {
  name: string;
  email: string;
  phone?: string;
  company?: string;
}

export interface BijouReply {
  text: string;
  booking?: BookingContact;
}

// SECURITY: Secure backend proxy implementation - no client-side API keys
export const sendMessageToBijou = async (
  history: { role: 'user' | 'model'; content: string }[],
  newMessage: string
): Promise<BijouReply> => {
  try {
    // Call secure backend API instead of client-side Gemini
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        history,
        message: newMessage
      })
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    const data = await response.json();
    return {
      text: data.response || "Sorry, my connection dropped for a second there. Could you say that again?",
      booking: data.booking,
    };

  } catch (error) {
    console.error("Error talking to Bijou:", error);
    
    // Graceful fallback — same US-English voice as api/chat.js.
    const fallbacks = [
      "Sorry, my connection is a bit slow right now. Could you try again?",
      "Hmm, our server hit a snag. Give me a moment and try again?",
      "Sorry, I ran into a technical issue on my end. Could you try that again?",
      "Technical problem on our side. You can also message us on WhatsApp: wa.me/60174106981"
    ];
    
    return { text: fallbacks[Math.floor(Math.random() * fallbacks.length)] ?? fallbacks[0]! };
  }
};