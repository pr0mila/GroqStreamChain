from pydantic import BaseModel
from typing import List, Optional


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatSession(BaseModel):
    id: str
    messages: List[Message] = []
    

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None