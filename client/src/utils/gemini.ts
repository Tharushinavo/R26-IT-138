/**
 * Gemini API integration for generating math hints
 * Uses Google's Gemini Flash model for AI-powered hints
 */
const GEMINI_API_KEY = 'AIzaSyDtMzAtBoSKSg9dp6Ao-CBzunb4HJbDiwY';
const GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent';

export interface GeminiHint {
  text: string;
  error?: string;
}

export async function generateMathHint(question: string, topic: string, language: 'en' | 'si' = 'en'): Promise<GeminiHint> {
  try {
    const langPrompt = language === 'si' ? 
      'Provide the hint in Sinhala language.' : 
      'Provide the hint in English language.';
      
    const prompt = `Provide a simple, child-friendly hint for this math problem. 
    Question: "${question}"
    Topic: ${topic}
    
    ${langPrompt}
    Give a hint that helps the student think through the problem step by step, but don't give away the answer. 
    Keep it very simple and encouraging, suitable for elementary school students.
    Maximum 2 sentences.`;

    const response = await fetch(`${GEMINI_URL}?key=${GEMINI_API_KEY}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              {
                text: prompt
              }
            ]
          }
        ]
      })
    });

    if (!response.ok) {
      throw new Error(`Gemini API error: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.candidates && data.candidates[0]?.content?.parts?.[0]?.text) {
      return { text: data.candidates[0].content.parts[0].text.trim() };
    } else {
      throw new Error('Invalid response format from Gemini');
    }
  } catch (error) {
    console.error('Gemini hint generation failed:', error);
    const fallbackText = language === 'si' ? 
      '💡 හුස්ම ගන්න, ප්‍රශ්නය නැවත කියවන්න. පියවර අනුව සිතන්න!' :
      '💡 Take a breath and read the question again. Think step by step!';
      
    return { 
      text: fallbackText,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}
