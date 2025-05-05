import uuid
import json
import asyncio
import logging
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models.chat import ChatSession, Message
from services.llm_service import LLMService
from config import HOST, PORT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Initialize LLM service
llm_service = LLMService()

# In-memory storage for chat sessions
chat_sessions: Dict[str, ChatSession] = {}

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        session_id = str(uuid.uuid4())
        self.active_connections[session_id] = websocket
        chat_sessions[session_id] = ChatSession(id=session_id)
        return session_id

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            logger.info(f"Disconnecting session {session_id}")
            del self.active_connections[session_id]


manager = ConnectionManager()


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    try:
        logger.info("New WebSocket connection attempt")
        session_id = await manager.connect(websocket)
        logger.info(f"Connected with session_id: {session_id}")
        
        # Send the session ID to the client
        await websocket.send_json({"type": "session_id", "session_id": session_id})
        logger.info(f"Sent session_id to client: {session_id}")
        
        # Send a welcome message
        welcome_message = "Hello! I'm your AI assistant GroqStreamChain. How can I help you today?"
        chat_sessions[session_id].messages.append(Message(role="assistant", content=welcome_message))
        await websocket.send_json({
            "type": "initial_message",
            "content": welcome_message
        })
        logger.info("Sent welcome message to client")
        
        while True:
            # Receive message from client
            logger.info("Waiting for client message")
            data = await websocket.receive_text()
            logger.info(f"Received message from client: {data[:50]}...")
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            # Add user message to session
            chat_sessions[session_id].messages.append(Message(role="user", content=user_message))
            
            # Send acknowledgment back to client
            await websocket.send_json({
                "type": "message_received",
                "status": "processing"
            })
            logger.info("Sent processing acknowledgment")
            
            try:
                # Stream AI response
                logger.info("Starting LLM response stream")
                full_response = ""
                async for response_chunk in llm_service.generate_response_stream(chat_sessions[session_id].messages):
                    logger.debug(f"Streaming chunk: {response_chunk[:20]}...")
                    await websocket.send_json({
                        "type": "stream",
                        "content": response_chunk
                    })
                    full_response += response_chunk
                
                # Add the complete AI response to the chat history
                chat_sessions[session_id].messages.append(Message(role="assistant", content=full_response))
                logger.info("LLM response complete, added to chat history")
                
                # Signal completion
                await websocket.send_json({
                    "type": "stream_end",
                    "session_id": session_id
                })
                logger.info("Sent stream_end signal")
                
            except Exception as e:
                logger.error(f"Error during LLM call: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": "Sorry, there was an error processing your request."
                })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally")
        if 'session_id' in locals():
            manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if 'session_id' in locals():
            manager.disconnect(session_id)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)