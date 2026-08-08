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
    return data.response || "Sorry boss, line breaking up a bit. Say again?";

  } catch (error) {
    console.error("Error talking to Bijou:", error);
    
    // Graceful fallback with cultural context
    const manglishFallbacks = [
      "Sorry boss, connection a bit slow. Can try again?",
      "Alamak! Server having issue. Give me a moment?", 
      "Aiyo, my brain lagging. Try again in a while boss?",
      "Technical problem on our side. WhatsApp us instead: wa.me/60174106981"
    ];
    
    return manglishFallbacks[Math.floor(Math.random() * manglishFallbacks.length)] ?? manglishFallbacks[0]!;
  }
};