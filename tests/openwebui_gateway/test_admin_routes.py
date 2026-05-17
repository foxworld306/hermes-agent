from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from openwebui_gateway.profile_service import ProfileService
from openwebui_gateway.tool_service import ToolService
from openwebui_gateway.session_manager import SessionManager


def _build_services(tmp_path):
    """Create isolated services pointing to tmp_path."""
    profile_service = ProfileService(profile_base_dir=str(tmp_path))
    tool_service = ToolService(config_path=str(tmp_path / "tool_config.yaml"))
    session_manager = SessionManager(
        profile_base_dir=str(tmp_path),
        tool_config_path=str(tmp_path / "tool_config.yaml"),
    )
    return profile_service, tool_service, session_manager


@pytest.fixture
def test_env(tmp_path):
    """Yield services with patches active for the whole test."""
    profile_service, tool_service, session_manager = _build_services(tmp_path)

    with (
        patch(
            "openwebui_gateway.routes.admin.profile_service", profile_service
        ),
        patch("openwebui_gateway.routes.admin.tool_service", tool_service),
        patch("openwebui_gateway.routes.admin.session_manager", session_manager),
    ):
        from importlib import reload

        import openwebui_gateway.main as main_mod

        reload(main_mod)

        yield TestClient(main_mod.app), profile_service, tool_service, session_manager


# ---------- GET /api/admin/users ----------


def test_admin_users_list_empty(test_env):
    """GET /api/admin/users returns only test profiles (may include global profiles)."""
    client, profile_svc, _, _ = test_env
    profile_svc.profile_base_dir.mkdir(parents=True, exist_ok=True)

    resp = client.get("/api/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # All returned profiles should have expected keys
    assert all("user_id" in u for u in data)


def test_admin_users_list_with_profiles(test_env):
    """GET /api/admin/users lists created profiles."""
    client, profile_svc, _, _ = test_env
    profile_svc.profile_base_dir.mkdir(parents=True, exist_ok=True)

    profile_svc.create_profile("alice@example.com")
    profile_svc.create_profile("bob@example.com")

    resp = client.get("/api/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    user_ids = {u["user_id"] for u in data}
    assert "alice@example.com" in user_ids
    assert "bob@example.com" in user_ids
    assert all("status" in u for u in data)


# ---------- GET /api/admin/users/{user_id} ----------


def test_admin_get_user_inactive(test_env):
    """GET /api/admin/users/{id} returns inactive for unknown user."""
    client, _, _, _ = test_env

    resp = client.get("/api/admin/users/nobody@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "nobody@example.com"
    assert data["status"] == "inactive"


def test_admin_get_user_active(test_env):
    """GET /api/admin/users/{id} returns active when agent exists."""
    client, _, _, session_mgr = test_env

    mock_agent = MagicMock()
    mock_agent._interrupt_requested = False
    session_mgr._active_agents["alice@example.com"] = mock_agent

    resp = client.get("/api/admin/users/alice@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"


# ---------- GET /api/admin/users/{user_id}/skills ----------


def test_admin_get_user_skills(test_env):
    """GET /api/admin/users/{id}/skills returns skill directories."""
    client, profile_svc, _, _ = test_env
    profile_svc.create_profile("alice@example.com")

    admin_dir = (
        profile_svc.get_profile_path("alice@example.com")
        / "skills"
        / "admin_installed"
        / "myskill"
    )
    admin_dir.mkdir(parents=True)

    resp = client.get("/api/admin/users/alice@example.com/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert "admin_installed" in data
    assert "myskill" in data["admin_installed"]


# ---------- POST /api/admin/tools/{name}/enable ----------


def test_admin_enable_tool(test_env):
    """POST /api/admin/tools/{name}/enable returns success."""
    client, _, tool_svc, _ = test_env

    resp = client.post("/api/admin/tools/web_search/enable")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "web_search" in data["message"]
    assert tool_svc.is_tool_enabled("web_search") is True


# ---------- POST /api/admin/tools/{name}/disable ----------


def test_admin_disable_tool(test_env):
    """POST /api/admin/tools/{name}/disable returns success."""
    client, _, tool_svc, _ = test_env

    resp = client.post("/api/admin/tools/terminal/disable")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "terminal" in data["message"]
    assert tool_svc.is_tool_enabled("terminal") is False


# ---------- GET /api/admin/tools ----------


def test_admin_list_tools(test_env):
    """GET /api/admin/tools returns all tool statuses."""
    client, _, _, _ = test_env

    resp = client.get("/api/admin/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all("tool_name" in t for t in data)
    assert all("enabled" in t for t in data)
    assert all("description" in t for t in data)


# ---------- POST /api/admin/agents/stop/{user_id} ----------


def test_admin_stop_agent_success(test_env):
    """POST /api/admin/agents/stop/{id} stops an active agent."""
    client, _, _, session_mgr = test_env

    mock_agent = MagicMock()
    mock_agent._interrupt_requested = False
    session_mgr._active_agents["alice@example.com"] = mock_agent

    resp = client.post("/api/admin/agents/stop/alice@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "stopped" in data["message"]


def test_admin_stop_agent_not_found(test_env):
    """POST /api/admin/agents/stop/{id} returns success=False for unknown user."""
    client, _, _, _ = test_env

    resp = client.post("/api/admin/agents/stop/nobody@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "not found" in data["message"]


# ---------- GET /api/admin/agents/running ----------


def test_admin_running_agents_empty(test_env):
    """GET /api/admin/agents/running returns empty list."""
    client, _, _, _ = test_env

    resp = client.get("/api/admin/agents/running")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_admin_running_agents_populated(test_env):
    """GET /api/admin/agents/running lists active agents."""
    client, _, _, session_mgr = test_env

    mock_agent = MagicMock()
    session_mgr._active_agents["alice@example.com"] = mock_agent

    resp = client.get("/api/admin/agents/running")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == "alice@example.com"
    assert data[0]["status"] == "active"


# ---------- GET /api/admin/system/stats ----------


def test_admin_system_stats(test_env):
    """GET /api/admin/system/stats returns expected fields."""
    client, profile_svc, _, _ = test_env
    profile_svc.profile_base_dir.mkdir(parents=True, exist_ok=True)

    profile_svc.create_profile("alice@example.com")

    resp = client.get("/api/admin/system/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "active_agents" in data
    assert "total_tools" in data
    assert "enabled_tools" in data
    assert data["total_users"] >= 1
    assert data["active_agents"] == 0


def test_admin_system_stats_with_agent(test_env):
    """GET /api/admin/system/stats counts active agents."""
    client, profile_svc, _, session_mgr = test_env
    profile_svc.profile_base_dir.mkdir(parents=True, exist_ok=True)

    mock_agent = MagicMock()
    session_mgr._active_agents["alice@example.com"] = mock_agent

    resp = client.get("/api/admin/system/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_agents"] == 1
