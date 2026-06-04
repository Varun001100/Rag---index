import google.generativeai as genai
from config.settings import settings
from utils.logger import logger
from models.conversation_model import Conversation
from typing import List

class LLMService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self._model = None

    def _get_model(self) -> genai.GenerativeModel:
        """Configures the google-generativeai SDK and retrieves the gemini-2.5-flash model instance."""
        if not self._model:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not set.")
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel("gemini-2.5-flash")
        return self._model

    def generate_answer(self, question: str, context: str, history: List[Conversation]) -> str:
        """
        Sends the compiled prompt containing context and chat history to the LLM.
        
        Args:
            question: The user's current query.
            context: Aggregated text from parent chunks.
            history: List of past Conversation turns for context.
            
        Returns:
            The model's textual answer.
        """
        logger.info("Generating response from Gemini 2.5 Flash.")
        
        # Compile historical chat turns
        if history:
            history_lines = []
            for turn in history:
                history_lines.append(f"User: {turn.question}")
                history_lines.append(f"Assistant: {turn.answer}")
            history_str = "\n".join(history_lines)
        else:
            history_str = "No previous conversation history."
            
        system_instruction = (
            "You are an advanced RAG assistant. You must answer the user's question based strictly and ONLY on the provided context below. "
            "Do not use any outside knowledge or general training knowledge to answer. Do not hallucinate or extrapolate. "
            "If the answer to the question is not explicitly or directly found in the provided context, you must respond EXACTLY with: "
            "\"I could not find that information in the uploaded documents.\""
        )
        
        prompt = f"""System Instructions:
{system_instruction}

Context:
{context}

Conversation History:
{history_str}

User Question: {question}
Answer:"""

        try:
            model = self._get_model()
            # Set temperature to 0 to prevent creative additions / hallucinations
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.0}
            )
            answer = response.text.strip()
            logger.info("Successfully received response from Gemini API.")
            return answer
        except Exception as e:
            logger.error(f"Gemini API generation failed: {str(e)}")
            raise e
