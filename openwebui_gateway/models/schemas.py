from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: List[Dict[str, Any]]

class UserProfileInfo(BaseModel):
    user_id: str
    status: Literal["active", "inactive", "creating"]
    skills_count: int = 0
    last_active: Optional[str] = None

class ToolStatus(BaseModel):
    tool_name: str
    enabled: bool
    description: str

class AdminActionResponse(BaseModel):
    success: bool
    message: str
