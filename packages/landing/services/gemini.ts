// SECURITY: Secure backend proxy implementation - no client-side API keys
export const sendMessageToBijou = async (
  history: { role: 'user' | 'model'; content: string }[],
  newMessage: string
): Promise<string> => {
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
    return data.response || "Sorry, my connection dropped for a second there. Could you say that again?";

  } catch (error) {
    console.error("Error talking to Bijou:", error);
    
    // Graceful fallback — same US-English voice as api/chat.js.
    const fallbacks = [
      "Sorry, my connection is a bit slow right now. Could you try again?",
      "Hmm, our server hit a snag. Give me a moment and try again?",
      "Sorry, I ran into a technical issue on my end. Could you try that again?",
      "Technical problem on our side. You can also message us on WhatsApp: wa.me/60174106981"
    ];
    
    return fallbacks[Math.floor(Math.random() * fallbacks.length)] ?? fallbacks[0]!;
  }
};