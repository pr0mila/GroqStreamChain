import asyncio
import logging
from typing import List, AsyncGenerator

from groq import Groq
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, AIMessage

from models.chat import Message
from config import GROQ_API_KEY, MODEL_NAME, LLM_CONFIG
from system_prompts import SYSTEM_PROMPT
# Configure logging
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.langchain_client = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name=MODEL_NAME,
            temperature=LLM_CONFIG["temperature"],
            max_tokens=LLM_CONFIG["max_tokens"],
        )

    def _convert_to_langchain_messages(self, messages: List[Message]):
        """Convert our message format to LangChain format"""
        lc_messages = []
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
        return lc_messages

    def _convert_to_groq_messages(self, messages: List[Message]):
        """Convert our message format to Groq format"""
        groq_messages = []
        for msg in messages:
            # Check if the message is a dictionary (like the system message)
            if isinstance(msg, dict):
                groq_messages.append({
                    "role": msg["role"], 
                    "content": msg["content"]
                })
            else:
                groq_messages.append({
                    "role": msg.role, 
                    "content": msg.content
                })
        return groq_messages

    async def generate_response_stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        """Generate streaming response directly with Groq client"""
        try:
            logger.info("Preparing LLM request")

            # Add system message to the list of messages
            system_message = {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
            messages.insert(0, system_message)  # Insert system message at the beginning
            
            # Convert messages to Groq format
            groq_messages = self._convert_to_groq_messages(messages)
            
            # Log the request (excluding full message content for privacy)
            logger.info(f"Sending request to Groq API with {len(groq_messages)} messages")
            
            # Create the completion with streaming enabled
            logger.info("Creating completion with Groq client")
            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=MODEL_NAME,
                messages=groq_messages,
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"],
                top_p=LLM_CONFIG["top_p"],
                stream=True,
                stop=LLM_CONFIG["stop"],
            )
            
            logger.info("Got streaming response from Groq API")
            
            # Stream the chunks back
            for chunk in completion:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
            
            logger.info("Finished streaming response")
            
        except Exception as e:
            logger.error(f"Error in LLM service: {e}", exc_info=True)
            yield "I'm sorry, I encountered an error processing your request."
