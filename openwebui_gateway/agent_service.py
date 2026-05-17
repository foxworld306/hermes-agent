import uuid
from typing import AsyncGenerator, List, Optional

from openwebui_gateway.session_manager import SessionManager


class AgentService:
    """Wrap AIAgent chat calls, providing OpenAI API compatible interface"""

    def __init__(self, profile_base_dir: str = "~/.hermes/profiles"):
        self.session_manager = SessionManager(profile_base_dir)

    def chat(
        self,
        user_id: str,
        message: str,
        model: str = "gpt-4",
        stream: bool = False,
    ):
        """Process a chat request for a user.

        Returns a string response (sync) or an async generator (stream).
        """
        agent = self.session_manager.get_or_create_agent(user_id)

        if stream:
            return self._stream_chat(agent, message)
        else:
            return self._sync_chat(agent, message)

    def _sync_chat(self, agent, message: str) -> str:
        """Synchronous chat — wraps agent.chat() with error handling.

        Returns the response string on success, or an error message string
        on failure (never raises).
        """
        try:
            response = agent.chat(message)
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    async def _stream_chat(
        self, agent, message: str
    ) -> AsyncGenerator[str, None]:
        """Stream chat response chunks (SSE-compatible).

        TODO: Implement real streaming. Currently returns the full response
        as a single chunk.
        """
        response = agent.chat(message)
        yield response

    def get_models(self) -> List[dict]:
        """Get available models in OpenAI API format"""
        return [
            {"id": "gpt-4", "object": "model"},
            {"id": "gpt-4-turbo", "object": "model"},
            {"id": "claude-3-opus", "object": "model"},
        ]

    def stop_agent(self, user_id: str) -> bool:
        """Stop a user's agent by delegating to SessionManager"""
        return self.session_manager.stop_agent(user_id)
