import asyncio
import threading
from pathlib import Path
from typing import Dict, Optional

from openwebui_gateway.profile_service import ProfileService
from openwebui_gateway.tool_service import ToolService


class SessionManager:
    """Manage user session and AIAgent instance lifecycle"""

    def __init__(
        self,
        profile_base_dir: str = "~/.hermes/profiles",
        tool_config_path: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.profile_service = ProfileService(profile_base_dir)
        self.tool_service = (
            ToolService(config_path=tool_config_path)
            if tool_config_path
            else ToolService()
        )
        
        # LLM endpoint configuration
        self.base_url = base_url
        self.api_key = api_key
        self.provider = provider

        self._active_agents: Dict[str, any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock = threading.Lock()

    def _get_lock(self, user_id: str) -> asyncio.Lock:
        """Get per-user asyncio lock (thread-safe access to dict of locks)"""
        with self._lock:
            if user_id not in self._locks:
                self._locks[user_id] = asyncio.Lock()
            return self._locks[user_id]

    def get_or_create_agent(self, user_id: str):
        """Get existing agent or create a new one for the user.

        Uses lazy import of run_agent.AIAgent to avoid circular dependencies.
        """
        if user_id in self._active_agents:
            return self._active_agents[user_id]

        # Ensure profile exists
        profile_path = self.profile_service.create_profile(user_id)

        # Lazy import to avoid circular dependency
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))

        try:
            from run_agent import AIAgent
        except ImportError:
            # Fallback: if AIAgent is unavailable (e.g., in minimal env),
            # create a lightweight stub so the gateway can still manage sessions
            AIAgent = _create_stub_agent()

        # Load user config
        config = self.profile_service.get_profile_config(user_id) or {}

        try:
            agent_kwargs = {
                "model": config.get("model", "gpt-4"),
                "max_iterations": 90,
                "save_trajectories": True,
                "session_id": user_id,
            }
            # Add LLM endpoint configuration if provided
            if self.base_url:
                agent_kwargs["base_url"] = self.base_url
            if self.api_key:
                agent_kwargs["api_key"] = self.api_key
            if self.provider:
                agent_kwargs["provider"] = self.provider
            
            agent = AIAgent(**agent_kwargs)
        except Exception:
            # If AIAgent init fails (missing API keys, etc.), fall back to stub
            agent = _create_stub_agent()(
                model="stub",
                max_iterations=90,
                save_trajectories=True,
                session_id=user_id,
            )

        self._active_agents[user_id] = agent
        return agent

    def get_agent(self, user_id: str) -> Optional[any]:
        """Get existing agent instance without creating one"""
        return self._active_agents.get(user_id)

    def stop_agent(self, user_id: str) -> bool:
        """Stop user agent: set interrupt flag and remove from active list"""
        agent = self._active_agents.get(user_id)
        if agent is None:
            return False

        # Set interrupt flag
        if hasattr(agent, "_interrupt_requested"):
            agent._interrupt_requested = True

        # Remove from active list
        del self._active_agents[user_id]
        return True

    def list_active_agents(self) -> list:
        """List all active agents"""
        return [
            {
                "user_id": user_id,
                "status": "active",
            }
            for user_id in self._active_agents.keys()
        ]

    def get_user_status(self, user_id: str) -> dict:
        """Get user status summary"""
        agent = self._active_agents.get(user_id)
        profile_exists = self.profile_service.profile_exists(user_id)

        return {
            "user_id": user_id,
            "profile_exists": profile_exists,
            "agent_active": agent is not None,
            "status": "active" if agent else "inactive",
        }


def _create_stub_agent():
    """Create a minimal AIAgent stub for testing/environments where AIAgent is unavailable."""

    class _StubAIAgent:
        def __init__(self, **kwargs):
            self.session_id = kwargs.get("session_id", "unknown")
            self.model = kwargs.get("model", "stub")
            self._interrupt_requested = False

        def chat(self, message: str) -> str:
            return f"Stub response to: {message}"

    return _StubAIAgent
