import tempfile
from unittest.mock import patch

import pytest

from openwebui_gateway.session_manager import SessionManager


@pytest.fixture
def manager(tmp_path):
    """Create a SessionManager with isolated temp directory"""
    return SessionManager(profile_base_dir=str(tmp_path), tool_config_path=str(tmp_path / "tool_config.yaml"))


class MockAIAgent:
    """Lightweight mock of run_agent.AIAgent for testing"""

    def __init__(self, **kwargs):
        self.session_id = kwargs.get("session_id", "unknown")
        self.model = kwargs.get("model", "gpt-4")
        self.max_iterations = kwargs.get("max_iterations", 90)
        self.save_trajectories = kwargs.get("save_trajectories", True)
        self._interrupt_requested = False
        self.enabled_toolsets = []

    def chat(self, message: str) -> str:
        return f"Mock response to: {message}"


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_get_or_create(manager):
    """get_or_create_agent returns an AIAgent instance (or stub) for user"""
    agent = manager.get_or_create_agent("user1@company.com")
    assert agent is not None
    assert hasattr(agent, "session_id") or hasattr(agent, "_StubAIAgent__dict__")


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_same_user_same_agent(manager):
    """Second call for same user returns the same agent instance"""
    agent1 = manager.get_or_create_agent("user1@company.com")
    agent2 = manager.get_or_create_agent("user1@company.com")
    assert agent1 is agent2


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_different_users_different_agents(manager):
    """Different users get different agent instances"""
    agent1 = manager.get_or_create_agent("user1@company.com")
    agent2 = manager.get_or_create_agent("user2@company.com")
    assert agent1 is not agent2


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_stop_agent(manager):
    """stop_agent sets interrupt flag and removes from active list"""
    agent = manager.get_or_create_agent("user1@company.com")
    assert agent is not None

    result = manager.stop_agent("user1@company.com")
    assert result is True
    assert manager.get_agent("user1@company.com") is None

    if hasattr(agent, "_interrupt_requested"):
        assert agent._interrupt_requested is True


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_stop_nonexistent_agent(manager):
    """stop_agent returns False for non-existent user"""
    result = manager.stop_agent("nobody@company.com")
    assert result is False


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_list_active_agents(manager):
    """list_active_agents returns all active agents"""
    manager.get_or_create_agent("user1@company.com")
    manager.get_or_create_agent("user2@company.com")

    agents = manager.list_active_agents()
    assert len(agents) == 2
    user_ids = {a["user_id"] for a in agents}
    assert "user1@company.com" in user_ids
    assert "user2@company.com" in user_ids
    assert all(a["status"] == "active" for a in agents)


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_get_user_status_inactive(manager):
    """get_user_status returns correct status for inactive user"""
    status = manager.get_user_status("nobody@company.com")
    assert status["user_id"] == "nobody@company.com"
    assert status["profile_exists"] is False
    assert status["agent_active"] is False
    assert status["status"] == "inactive"


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_get_user_status_active(manager):
    """get_user_status returns correct status for active user"""
    manager.get_or_create_agent("user1@company.com")

    status = manager.get_user_status("user1@company.com")
    assert status["user_id"] == "user1@company.com"
    assert status["profile_exists"] is True
    assert status["agent_active"] is True
    assert status["status"] == "active"


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_uses_threading_lock(manager):
    """SessionManager uses threading.Lock for dict access and asyncio.Lock per-user"""
    import threading
    import asyncio

    assert isinstance(manager._lock, type(threading.Lock()))

    lock = manager._get_lock("user1")
    assert isinstance(lock, asyncio.Lock)

    # Same user returns same lock
    lock2 = manager._get_lock("user1")
    assert lock is lock2


@patch.dict("sys.modules", {"run_agent": None})
def test_session_manager_profile_created(manager, tmp_path):
    """get_or_create_agent ensures profile directory exists"""
    manager.get_or_create_agent("newuser@company.com")

    profile_path = manager.profile_service.get_profile_path("newuser@company.com")
    assert profile_path.exists()
    assert (profile_path / "config.yaml").exists()


def test_session_manager_with_mocked_aiagent(tmp_path):
    """get_or_create_agent works with mocked AIAgent import"""
    import types

    tool_config = tmp_path / "tool_config.yaml"
    mgr = SessionManager(profile_base_dir=str(tmp_path), tool_config_path=str(tool_config))

    mock_run_agent = types.ModuleType("run_agent")
    mock_run_agent.AIAgent = MockAIAgent

    with patch.dict("sys.modules", {"run_agent": mock_run_agent}):
        agent = mgr.get_or_create_agent("user1@company.com")

    assert isinstance(agent, MockAIAgent)
    assert agent.session_id == "user1@company.com"
