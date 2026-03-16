import os
import logging
from dotenv import load_dotenv
from groq import Groq
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self):
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.emergent_api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        self.use_groq = bool(self.groq_api_key)
        
        if not self.groq_api_key and not self.emergent_api_key:
            raise ValueError("Neither GROQ_API_KEY nor EMERGENT_LLM_KEY found in environment")
    
    async def create_chat(self, system_message: str, session_id: str):
        """For Emergent LLM compatibility"""
        if not self.use_groq and self.emergent_api_key:
            chat = LlmChat(
                api_key=self.emergent_api_key,
                session_id=session_id,
                system_message=system_message
            )
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            return chat
        return None
    
    async def send_message(self, chat_or_system: any, message: str) -> str:
        """Send message with Groq primary, Emergent fallback"""
        try:
            # Try Groq first
            if self.use_groq and self.groq_client:
                try:
                    # If chat_or_system is a string, it's the system message
                    system_message = chat_or_system if isinstance(chat_or_system, str) else "You are a helpful AI assistant."
                    
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": message}
                        ],
                        model="llama-3.3-70b-versatile",
                        temperature=0.7,
                        max_tokens=2000,
                    )
                    
                    response = chat_completion.choices[0].message.content
                    logger.info("✓ Response from Groq")
                    return response
                    
                except Exception as groq_error:
                    logger.warning(f"Groq failed, falling back to Emergent LLM: {groq_error}")
                    # Fall through to Emergent LLM
            
            # Fallback to Emergent LLM
            if self.emergent_api_key:
                logger.info("Using Emergent LLM (fallback)")
                
                # Create or use existing chat
                if isinstance(chat_or_system, str):
                    # chat_or_system is system message, create new chat
                    chat = LlmChat(
                        api_key=self.emergent_api_key,
                        session_id="fallback_session",
                        system_message=chat_or_system
                    )
                    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
                else:
                    # chat_or_system is existing chat object
                    chat = chat_or_system
                
                user_message = UserMessage(text=message)
                response = await chat.send_message(user_message)
                return response
            
            return "Unable to process request - no LLM available"
            
        except Exception as e:
            logger.error(f"Error in send_message: {e}")
            return "Error processing request"
