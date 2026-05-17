from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request

from openwebui_gateway.session_manager import SessionManager
from openwebui_gateway.profile_service import ProfileService
from openwebui_gateway.tool_service import ToolService

router = APIRouter(prefix="/api/admin")

session_manager = SessionManager()
profile_service = ProfileService()
tool_service = ToolService()


@router.get("/users")
async def list_users():
    """List all user profiles."""
    profiles = profile_service.list_profiles()
    return [
        {
            "user_id": p["user_id"],
            "status": "active",
            "created_at": p["created"],
            "profile_path": p["path"],
        }
        for p in profiles
    ]


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get user status and details."""
    status = session_manager.get_user_status(user_id)
    return status


@router.get("/users/{user_id}/skills")
async def get_user_skills(user_id: str):
    """Get user skills list."""
    profile_path = profile_service.get_profile_path(user_id)
    skills = {"admin_installed": [], "user_installed": []}

    admin_dir = profile_path / "skills" / "admin_installed"
    if admin_dir.exists():
        skills["admin_installed"] = [d.name for d in admin_dir.iterdir() if d.is_dir()]

    user_dir = profile_path / "skills" / "user_installed"
    if user_dir.exists():
        skills["user_installed"] = [d.name for d in user_dir.iterdir() if d.is_dir()]

    return skills


@router.post("/tools/{tool_name}/enable")
async def enable_tool(tool_name: str):
    """Enable a tool globally."""
    tool_service.enable_tool(tool_name)
    return {"success": True, "message": f"Tool {tool_name} enabled"}


@router.post("/tools/{tool_name}/disable")
async def disable_tool(tool_name: str):
    """Disable a tool globally."""
    tool_service.disable_tool(tool_name)
    return {"success": True, "message": f"Tool {tool_name} disabled"}


@router.get("/tools")
async def list_tools():
    """List all tool status."""
    return tool_service.get_tool_status()


@router.post("/agents/stop/{user_id}")
async def stop_agent(user_id: str):
    """Stop a user's agent."""
    success = session_manager.stop_agent(user_id)
    return {
        "success": success,
        "message": f"Agent for {user_id} stopped" if success else "Agent not found",
    }


@router.get("/agents/running")
async def list_running_agents():
    """List running agents."""
    return session_manager.list_active_agents()


@router.get("/system/stats")
async def system_stats():
    """System statistics."""
    profiles = profile_service.list_profiles()
    active_agents = session_manager.list_active_agents()

    return {
        "total_users": len(profiles),
        "active_agents": len(active_agents),
        "total_tools": len(tool_service.get_tool_status()),
        "enabled_tools": len(
            [t for t in tool_service.get_tool_status() if t["enabled"]]
        ),
    }


@router.get("/dashboard")
async def admin_dashboard(request: Request):
    """Admin dashboard HTML page."""
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})
