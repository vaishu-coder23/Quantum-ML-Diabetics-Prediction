import google.generativeai as genai
import time

class ChatbotService:
    def __init__(self, api_key=None):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
            # Using gemini-2.5-flash for maximum intelligence in this environment
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.model = None

    def get_response(self, user_query, patient_context=None):
        if not self.model:
            return "AI Advisor is currently in offline mode. Please contact administrator to enable Gemini API."

        # System prompt for health advisor context
        system_prompt = (
            "You are 'Quantum Health Advisor', a specialized medical AI assistant focusing on diabetes risk."
            " Your tone should be empathetic, supportive, and professionally encouraging—like a caring family doctor."
            " Guidelines:"
            " 1. Provide clear, actionable dietary advice (focus on low-GI, whole foods) in a non-judgmental way."
            " 2. Suggest metabolic-focused exercises that are easy to start (e.g., brisk walking, swimming)."
            " 3. If a user asks about medications, recommend standard non-prescription support where safe, and always advise consulting their primary physician for clinical prescriptions."
            " 4. Personalize every response using the provided patient history context (risk scores and trends)."
            " 5. Structure your answers with friendly bullet points for easy reading."
            " 6. Keep responses concise and human — avoid overly long answers."
            " 7. Always end with a short supportive phrase like 'We are in this together!' or 'Keep up the great effort!'"
        )

        full_prompt = f"{system_prompt}\n\nPatient History Context: {patient_context or 'No history available.'}\n\nUser Question: {user_query}"

        # Retry up to 3 times with backoff for rate limits
        for attempt in range(3):
            try:
                response = self.model.generate_content(full_prompt)
                return response.text
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower() or "Resource has been exhausted" in error_msg:
                    if attempt < 2:
                        time.sleep(2 ** attempt)  # 1s, 2s
                        continue
                    return "The AI is receiving many requests right now. Please try again in a moment!"
                elif "404" in error_msg or "not found" in error_msg.lower():
                    return "AI model configuration error. Please contact the administrator."
                return "I'm sorry, I'm having trouble connecting right now. Please try again shortly."

if __name__ == "__main__":
    bot = ChatbotService(api_key="TEST_KEY")
