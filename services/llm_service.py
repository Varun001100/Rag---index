import os
from google import genai
from google.genai import types
from config.settings import Config


class LlmService:

    _api_keys = []
    _models = []
    _clients = {}  # Cache Client instances per API key
    _current_key_idx = 0
    _current_model_idx = 0
    _initialized = False

    @classmethod
    def initialize_rotation(cls):
        """
        Loads configured API keys and models for round-robin rotation.
        """
        if cls._initialized:
            return

        # Load keys
        keys_str = Config.GEMINI_API_KEYS
        if keys_str:
            cls._api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            cls._api_keys = []

        if not cls._api_keys and Config.GEMINI_API_KEY:
            cls._api_keys = [Config.GEMINI_API_KEY]

        # Load models
        models_str = Config.GEMINI_MODELS
        if models_str:
            cls._models = [m.strip() for m in models_str.split(",") if m.strip()]
        else:
            cls._models = []

        if not cls._models:
            cls._models = [Config.GEMINI_MODEL]

        cls._current_key_idx = 0
        cls._current_model_idx = 0
        cls._initialized = True

    @classmethod
    def get_client_by_key(cls, api_key):
        """
        Gets or creates a GenAI Client instance for the specified API key.
        """
        if api_key not in cls._clients:
            cls._clients[api_key] = genai.Client(api_key=api_key)
        return cls._clients[api_key]

    @classmethod
    def get_client(cls):
        """
        Fallback implementation for compatibility with other parts of the application.
        """
        cls.initialize_rotation()
        if cls._api_keys:
            return cls.get_client_by_key(cls._api_keys[0])
        return genai.Client(api_key=Config.GEMINI_API_KEY)

    @classmethod
    def generate_answer(cls, query, chunks, history):
        """
        Generates an answer using Gemini, leveraging conversation history
        and retrieved parent chunks as context, with round-robin failover.
        """
        cls.initialize_rotation()

        if not cls._api_keys:
            return "Error: No Gemini API keys configured. Please set GEMINI_API_KEY or GEMINI_API_KEYS in .env."

        # Format context chunks
        context_text = ""
        if chunks:
            context_text += "\n--- RETRIEVED DOCUMENT CONTEXT ---\n"
            for chunk in chunks:
                context_text += (
                    f"[Source Document: {chunk['filename']}, Page: {chunk['page_number']}]\n"
                    f"{chunk['text']}\n\n"
                )
        else:
            context_text += "\nNo document context is available for this session.\n"

        # Format conversation history (up to recent limit)
        history_text = ""
        if history:
            history_text += "\n--- RECENT CONVERSATION HISTORY ---\n"
            for turn in history:
                history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n\n"

        # Construct final prompt
        prompt = f"""
Use the retrieved document context and the conversation history above to answer the User Question at the end.

INSTRUCTIONS:
1. Provide a direct, helpful, and factually accurate answer.
2. Rely only on the provided context. If the answer cannot be found or inferred from the context, state: "I cannot find the answer in the uploaded documents."
3. Do not make up facts or use external knowledge not present in the documents.

{context_text}
{history_text}
User Question: {query}
Answer:"""

        system_instruction = (
            "You are a production-grade Multi-Document RAG assistant. "
            "Your sole objective is to answer the user's questions truthfully and accurately using ONLY "
            "the provided context from their uploaded PDF documents. "
            "Never hallucinate or refer to external facts."
        )

        total_attempts = len(cls._api_keys) * len(cls._models)
        last_error = None

        for attempt in range(total_attempts):
            api_key = cls._api_keys[cls._current_key_idx]
            model = cls._models[cls._current_model_idx]

            try:
                client = cls.get_client_by_key(api_key)
                
                print(f"[LLM] Attempt {attempt+1}/{total_attempts}: Using model '{model}' with key index {cls._current_key_idx}")
                
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                    )
                )
                
                # Request succeeded: advance rotation pointers for the next query
                cls._current_key_idx = (cls._current_key_idx + 1) % len(cls._api_keys)
                cls._current_model_idx = (cls._current_model_idx + 1) % len(cls._models)
                
                return response.text

            except Exception as e:
                last_error = e
                print(f"[LLM] Attempt {attempt+1} failed with model '{model}' & key index {cls._current_key_idx}. Error: {e}")
                
                # Attempt failed: failover to next key and next model for subsequent attempt
                cls._current_key_idx = (cls._current_key_idx + 1) % len(cls._api_keys)
                cls._current_model_idx = (cls._current_model_idx + 1) % len(cls._models)

        # If all combinations of keys and models failed
        return f"Error: Failed to generate response from Gemini after trying all configured keys and models. Details: {str(last_error)}"
