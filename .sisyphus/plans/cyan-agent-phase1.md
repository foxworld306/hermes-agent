# Phase 1: Cyan Agent Open-WebUI Integration Implementation Plan

**Goal:** Create a FastAPI Gateway that serves as an OpenAI API-compatible backend for Open-WebUI, enabling 600+ enterprise users to each have their own isolated Cyan Agent (via Hermes profiles).

**Architecture:** Add a new `openwebui_gateway/` directory with FastAPI endpoints, a SessionManager for per-user agent lifecycle, ProfileService for lazy profile creation, and ToolService for admin-managed global tool control. Minimal changes to existing Hermes core code.

**Tech Stack:** FastAPI, Pydantic, SSE streaming, SQLite, asyncio. Existing Hermes: run_agent.py, cli.py, hermes_state.py, model_tools.py.

**Port:** 18080 (uncommon port to avoid conflicts)

---

## File Structure (New Files)

```
openwebui_gateway/                    # NEW: Gateway service
├── __init__.py
├── main.py                           # FastAPI app factory
├── config.py                         # GatewayConfig dataclass
├── auth.py                           # JWT token validation, user extraction
├── session_manager.py                # SessionManager: agent lifecycle
├── profile_service.py                # ProfileService: profile CRUD
├── tool_service.py                   # ToolService: global tool enable/disable
├── agent_service.py                  # AgentService: AIAgent wrapper
├── models/
│   ├── __init__.py
│   └── schemas.py                    # Pydantic request/response models
├── routes/
│   ├── __init__.py
│   ├── openai.py                     # /v1/chat/completions, /v1/models, /health
│   └── admin.py                      # /api/admin/* endpoints
└── templates/
    └── admin_dashboard.html          # Simple Jinja2 admin UI

tests/openwebui_gateway/              # NEW: Test suite
├── __init__.py
├── conftest.py
├── test_gateway.py
├── test_session_manager.py
├── test_profile_service.py
└── test_tool_service.py
```

---

## Task 1: Scaffold Gateway Module

**Status:** ✅ COMPLETE

**Files:**
- Create: `openwebui_gateway/__init__.py`
- Create: `openwebui_gateway/config.py`
- Create: `openwebui_gateway/models/schemas.py`
- Create: `tests/openwebui_gateway/__init__.py`

```python
# Step 1: Write unit test for GatewayConfig
# tests/openwebui_gateway/test_gateway.py

def test_gateway_config_default():
    from openwebui_gateway.config import GatewayConfig
    config = GatewayConfig()
    assert config.host == "0.0.0.0"
    assert config.openai_port == 18080
    assert config.max_concurrent_agents == 50
```

```bash
# Step 2: Run test to verify it fails
python -m pytest tests/openwebui_gateway/test_gateway.py::test_gateway_config_default -v
# Expected: FAIL (ModuleNotFoundError or ImportError)
```

```python
# Step 3: Implement GatewayConfig dataclass
# openwebui_gateway/config.py

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GatewayConfig:
    host: str = "0.0.0.0"
    openai_port: int = 18080
    max_concurrent_agents: int = 50
    profile_base_dir: str = "~/.hermes/profiles"
    admin_secret: Optional[str] = None
    allowed_models: List[str] = field(default_factory=list)
    default_model: str = "gpt-4"
```

```python
# Step 4: Implement base schemas
# openwebui_gateway/models/schemas.py

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
```

```bash
# Step 5: Run tests to verify they pass
python -m pytest tests/openwebui_gateway/test_gateway.py -v
# Expected: PASS

# Step 6: Commit
git add openwebui_gateway/ tests/openwebui_gateway/
git commit -m "feat(gateway): scaffold gateway module with config and schemas"
```

---

## Task 2: Profile Service

**Status:** ✅ COMPLETE

**Files:**
- Create: `openwebui_gateway/profile_service.py`
- Create: `tests/openwebui_gateway/test_profile_service.py`

```python
# Step 1: Write test for profile creation
# tests/openwebui_gateway/test_profile_service.py

import pytest
import tempfile
import shutil
from pathlib import Path
from openwebui_gateway.profile_service import ProfileService

def test_create_profile():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ProfileService(profile_base_dir=tmpdir)
        user_id = "test_user@company.com"
        
        profile_path = service.create_profile(user_id)
        
        assert profile_path.exists()
        assert (profile_path / "config.yaml").exists()
        assert (profile_path / "sessions.db").exists()
        assert (profile_path / "skills/admin_installed").exists()
        assert (profile_path / "skills/user_installed").exists()
```

```bash
# Step 2: Run test to verify it fails
python -m pytest tests/openwebui_gateway/test_profile_service.py::test_create_profile -v
# Expected: FAIL (ImportError)
```

```python
# Step 3: Implement ProfileService
# openwebui_gateway/profile_service.py

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional
import yaml

class ProfileService:
    """Manage user profile directory creation, queries, and sync"""
    
    def __init__(self, profile_base_dir: str = "~/.hermes/profiles"):
        self.profile_base_dir = Path(profile_base_dir).expanduser()
        self.profile_base_dir.mkdir(parents=True, exist_ok=True)
        self.global_config_path = Path("~/.hermes/config.yaml").expanduser()
    
    def _sanitize_user_id(self, user_id: str) -> str:
        """Convert user_id to safe directory name"""
        safe = "".join(c if c.isalnum() or c in "-_@." else "_" for c in user_id)
        return safe
    
    def get_profile_path(self, user_id: str) -> Path:
        """Get user profile directory path"""
        safe_id = self._sanitize_user_id(user_id)
        return self.profile_base_dir / safe_id
    
    def profile_exists(self, user_id: str) -> bool:
        """Check if user profile exists"""
        return self.get_profile_path(user_id).exists()
    
    def create_profile(self, user_id: str) -> Path:
        """Create new user profile"""
        profile_path = self.get_profile_path(user_id)
        
        if profile_path.exists():
            return profile_path
        
        # Create directory structure
        profile_path.mkdir(parents=True, exist_ok=True)
        (profile_path / "skills" / "admin_installed").mkdir(parents=True)
        (profile_path / "skills" / "user_installed").mkdir(parents=True)
        
        # Copy global default config
        default_config = self._load_default_config()
        with open(profile_path / "config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        
        # Initialize SQLite DB
        self._init_database(profile_path / "sessions.db")
        
        # Sync global skills
        self._sync_global_skills(profile_path)
        
        return profile_path
    
    def _load_default_config(self) -> dict:
        """Load global default config"""
        if self.global_config_path.exists():
            with open(self.global_config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _init_database(self, db_path: Path):
        """Initialize SQLite database"""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def _sync_global_skills(self, profile_path: Path):
        """Sync global skills to newly created profile"""
        global_skills_dir = Path("~/.hermes/skills").expanduser()
        admin_installed_dir = profile_path / "skills" / "admin_installed"
        
        if global_skills_dir.exists():
            for skill_dir in global_skills_dir.iterdir():
                if skill_dir.is_dir() and skill_dir.name not in [".archive", ".usage.json"]:
                    target = admin_installed_dir / skill_dir.name
                    if not target.exists():
                        shutil.copytree(skill_dir, target)
    
    def list_profiles(self) -> list:
        """List all created profiles"""
        profiles = []
        for profile_dir in self.profile_base_dir.iterdir():
            if profile_dir.is_dir():
                profiles.append({
                    "user_id": profile_dir.name,
                    "path": str(profile_dir),
                    "created": profile_dir.stat().st_ctime
                })
        return profiles
    
    def get_profile_config(self, user_id: str) -> Optional[dict]:
        """Get user profile config"""
        config_path = self.get_profile_path(user_id) / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return None
    
    def delete_profile(self, user_id: str) -> bool:
        """Delete user profile (dangerous!)"""
        profile_path = self.get_profile_path(user_id)
        if profile_path.exists():
            shutil.rmtree(profile_path)
            return True
        return False
```

```bash
# Step 4: Run tests to verify they pass
python -m pytest tests/openwebui_gateway/test_profile_service.py -v
# Expected: PASS

# Step 5: Commit
git add openwebui_gateway/profile_service.py tests/openwebui_gateway/test_profile_service.py
git commit -m "feat(gateway): implement ProfileService for user profile management"
```

---

## Task 3: Tool Service

**Status:** ✅ COMPLETE

**Files:**
- Create: `openwebui_gateway/tool_service.py`
- Create: `tests/openwebui_gateway/test_tool_service.py`

```python
# Step 1: Write test for tool enable/disable
# tests/openwebui_gateway/test_tool_service.py

def test_tool_enable_disable():
    import tempfile
    from openwebui_gateway.tool_service import ToolService
    
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ToolService(config_path=tmpdir + "/config.yaml")
        
        # Initially all tools should be enabled
        assert service.is_tool_enabled("web_search") is True
        
        # Disable a tool
        service.disable_tool("web_search")
        assert service.is_tool_enabled("web_search") is False
        
        # Re-enable
        service.enable_tool("web_search")
        assert service.is_tool_enabled("web_search") is True
```

```bash
# Step 2: Run test to verify it fails
python -m pytest tests/openwebui_gateway/test_tool_service.py::test_tool_enable_disable -v
# Expected: FAIL
```

```python
# Step 3: Implement ToolService
# openwebui_gateway/tool_service.py

import yaml
from pathlib import Path
from typing import List, Optional, Dict
import os

class ToolService:
    """Manage global tool enable/disable status"""
    
    def __init__(self, config_path: str = "~/.hermes/config.yaml"):
        self.config_path = Path(config_path).expanduser()
        self.admin_config_key = "admin"
        self.tools_key = "tools"
        self.enabled_key = "enabled"
        self._ensure_admin_config()
    
    def _ensure_admin_config(self):
        """Ensure admin config section exists"""
        config = self._load_config()
        if self.admin_config_key not in config:
            config[self.admin_config_key] = {}
        if self.tools_key not in config[self.admin_config_key]:
            config[self.admin_config_key][self.tools_key] = {}
        if self.enabled_key not in config[self.admin_config_key][self.tools_key]:
            config[self.admin_config_key][self.tools_key][self.enabled_key] = []
        self._save_config(config)
    
    def _load_config(self) -> dict:
        """Load config file"""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _save_config(self, config: dict):
        """Save config file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    def _get_disabled_tools(self) -> List[str]:
        """Get disabled tools list (using enabled whitelist)"""
        config = self._load_config()
        enabled = config.get(self.admin_config_key, {}).get(self.tools_key, {}).get(self.enabled_key, [])
        
        if not enabled:
            return []
        
        all_tools = self._get_all_available_tools()
        return [t for t in all_tools if t not in enabled]
    
    def _get_all_available_tools(self) -> List[str]:
        """Get all available tool names (hardcoded for Phase 1)"""
        return [
            "web_search", "terminal", "file", "code_execution",
            "browser", "memory", "todo", "vision"
        ]
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if tool is enabled"""
        disabled = self._get_disabled_tools()
        return tool_name not in disabled
    
    def enable_tool(self, tool_name: str):
        """Enable tool (add to enabled list)"""
        config = self._load_config()
        enabled = config.get(self.admin_config_key, {}).get(self.tools_key, {}).get(self.enabled_key, [])
        
        if tool_name not in enabled:
            enabled.append(tool_name)
            config[self.admin_config_key][self.tools_key][self.enabled_key] = enabled
            self._save_config(config)
    
    def disable_tool(self, tool_name: str):
        """Disable tool (remove from enabled list)"""
        config = self._load_config()
        enabled = config.get(self.admin_config_key, {}).get(self.tools_key, {}).get(self.enabled_key, [])
        
        if tool_name in enabled:
            enabled.remove(tool_name)
            config[self.admin_config_key][self.tools_key][self.enabled_key] = enabled
            self._save_config(config)
    
    def get_tool_status(self) -> List[Dict]:
        """Get all tool status list"""
        all_tools = self._get_all_available_tools()
        disabled = self._get_disabled_tools()
        
        return [
            {
                "tool_name": tool,
                "enabled": tool not in disabled,
                "description": self._get_tool_description(tool)
            }
            for tool in all_tools
        ]
    
    def _get_tool_description(self, tool_name: str) -> str:
        """Get tool description"""
        descriptions = {
            "web_search": "Search the web for information",
            "terminal": "Execute commands in terminal",
            "file": "Read and write files",
            "code_execution": "Execute code snippets",
            "browser": "Navigate and interact with web pages",
            "memory": "Store and retrieve memories",
            "todo": "Manage todo lists",
            "vision": "Analyze images and vision content"
        }
        return descriptions.get(tool_name, "No description available")
    
    def filter_tools(self, tools: List[str]) -> List[str]:
        """Filter out disabled tools"""
        disabled = self._get_disabled_tools()
        if not disabled:
            return tools
        return [t for t in tools if t not in disabled]
```

```bash
# Step 4: Run tests to verify they pass
python -m pytest tests/openwebui_gateway/test_tool_service.py -v
# Expected: PASS

# Step 5: Commit
git add openwebui_gateway/tool_service.py tests/openwebui_gateway/test_tool_service.py
git commit -m "feat(gateway): implement ToolService for admin tool control"
```

---

## Task 4: Session Manager

**Status:** ✅ COMPLETE

**Files:**
- Create: `openwebui_gateway/session_manager.py`
- Create: `tests/openwebui_gateway/test_session_manager.py`

```python
# Step 1: Write test for session manager
# tests/openwebui_gateway/test_session_manager.py

def test_session_manager_get_or_create():
    import tempfile
    from openwebui_gateway.session_manager import SessionManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager(profile_base_dir=tmpdir)
        
        # Create or get agent for user
        agent = manager.get_or_create_agent("user1@company.com")
        assert agent is not None
        
        # Second call should return same agent
        agent2 = manager.get_or_create_agent("user1@company.com")
        assert agent is agent2
        
        # Different user should get different agent
        agent3 = manager.get_or_create_agent("user2@company.com")
        assert agent3 is not agent
```

```bash
# Step 2: Run test to verify it fails
python -m pytest tests/openwebui_gateway/test_session_manager.py::test_session_manager_get_or_create -v
# Expected: FAIL
```

```python
# Step 3: Implement SessionManager
# openwebui_gateway/session_manager.py

import asyncio
import threading
from typing import Dict, Optional
from pathlib import Path

from openwebui_gateway.profile_service import ProfileService
from openwebui_gateway.tool_service import ToolService

class SessionManager:
    """Manage user Session and AIAgent instance lifecycle"""
    
    def __init__(self, profile_base_dir: str = "~/.hermes/profiles"):
        self.profile_service = ProfileService(profile_base_dir)
        self.tool_service = ToolService()
        
        self._active_agents: Dict[str, any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock = threading.Lock()
    
    def _get_lock(self, user_id: str) -> asyncio.Lock:
        """Get user lock (for concurrency safety)"""
        with self._lock:
            if user_id not in self._locks:
                self._locks[user_id] = asyncio.Lock()
            return self._locks[user_id]
    
    def get_or_create_agent(self, user_id: str):
        """Get or create user AIAgent instance"""
        if user_id in self._active_agents:
            return self._active_agents[user_id]
        
        # Ensure profile exists
        profile_path = self.profile_service.create_profile(user_id)
        
        # Import Hermes AIAgent (lazy import to avoid circular dependency)
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from run_agent import AIAgent
        
        # Load user config
        config = self.profile_service.get_profile_config(user_id) or {}
        
        # Create agent instance
        agent = AIAgent(
            model=config.get("model", "gpt-4"),
            max_iterations=90,
            save_trajectories=True,
            session_id=user_id,
        )
        
        # Filter available tools based on global settings
        enabled_tools = self.tool_service.filter_tools(agent.enabled_toolsets)
        agent.enabled_toolsets = enabled_tools
        
        self._active_agents[user_id] = agent
        return agent
    
    def get_agent(self, user_id: str) -> Optional[any]:
        """Get existing agent instance"""
        return self._active_agents.get(user_id)
    
    def stop_agent(self, user_id: str) -> bool:
        """Stop user agent"""
        agent = self._active_agents.get(user_id)
        if agent is None:
            return False
        
        # Set interrupt flag
        if hasattr(agent, '_interrupt_requested'):
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
            "status": "active" if agent else "inactive"
        }
```

```bash
# Step 4: Run tests to verify they pass
python -m pytest tests/openwebui_gateway/test_session_manager.py -v
# Expected: PASS

# Step 5: Commit
git add openwebui_gateway/session_manager.py tests/openwebui_gateway/test_session_manager.py
git commit -m "feat(gateway): implement SessionManager for agent lifecycle"
```

---

## Task 5: Agent Service Wrapper

**Files:**
- Create: `openwebui_gateway/agent_service.py`
- Create: `tests/openwebui_gateway/test_agent_service.py`

```python
# Step 1: Write test for agent chat
# tests/openwebui_gateway/test_agent_service.py

def test_agent_chat():
    import tempfile
    from openwebui_gateway.agent_service import AgentService
    
    with tempfile.TemporaryDirectory() as tmpdir:
        service = AgentService(profile_base_dir=tmpdir)
        
        # Mock test (cannot call LLM in unit tests)
        response = service.chat("user1", "Hello")
        assert isinstance(response, str)
        assert len(response) > 0
```

```bash
# Step 2: Run test to verify it fails
python -m pytest tests/openwebui_gateway/test_agent_service.py::test_agent_chat -v
# Expected: FAIL
```

```python
# Step 3: Implement AgentService
# openwebui_gateway/agent_service.py

import uuid
from typing import AsyncGenerator, Dict, Optional
from pathlib import Path

from openwebui_gateway.session_manager import SessionManager

class AgentService:
    """Wrap AIAgent chat calls, providing OpenAI API compatible interface"""
    
    def __init__(self, profile_base_dir: str = "~/.hermes/profiles"):
        self.session_manager = SessionManager(profile_base_dir)
    
    def chat(self, user_id: str, message: str, model: str = "gpt-4", stream: bool = False):
        """Synchronous chat call"""
        agent = self.session_manager.get_or_create_agent(user_id)
        
        if stream:
            return self._stream_chat(agent, message)
        else:
            return self._sync_chat(agent, message)
    
    def _sync_chat(self, agent, message: str) -> str:
        """Synchronous chat"""
        try:
            response = agent.chat(message)
            return response
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _stream_chat(self, agent, message: str) -> AsyncGenerator[str, None]:
        """Stream chat (SSE)"""
        # TODO: Implement real streaming
        response = agent.chat(message)
        yield response
    
    def get_models(self) -> list:
        """Get available models list"""
        return [
            {"id": "gpt-4", "object": "model"},
            {"id": "gpt-4-turbo", "object": "model"},
            {"id": "claude-3-opus", "object": "model"},
        ]
    
    def stop_agent(self, user_id: str) -> bool:
        """Stop user agent"""
        return self.session_manager.stop_agent(user_id)
```

```bash
# Step 4: Run tests to verify they pass
python -m pytest tests/openwebui_gateway/test_agent_service.py -v
# Expected: PASS

# Step 5: Commit
git add openwebui_gateway/agent_service.py tests/openwebui_gateway/test_agent_service.py
git commit -m "feat(gateway): implement AgentService wrapper for AIAgent"
```

---

## Task 6: OpenAI API Routes

**Status:** ✅ COMPLETE

**Files:**
- Create: `openwebui_gateway/routes/openai.py`
- Create: `openwebui_gateway/routes/__init__.py`
- Create: `tests/openwebui_gateway/test_openai_routes.py`

```python
# Step 1: Write test for chat completions endpoint
# tests/openwebui_gateway/test_openai_routes.py

def test_chat_completions():
    from fastapi.testclient import TestClient
    from openwebui_gateway.main import app
    
    client = TestClient(app)
    
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        },
        headers={"X-User-Id": "test@company.com"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
```

```bash
# Step 2: Run test to verify it fails
python -m pytest tests/openwebui_gateway/test_openai_routes.py::test_chat_completions -v
# Expected: FAIL
```

```python
# Step 3: Implement OpenAI routes
# openwebui_gateway/routes/__init__.py

from .openai import router as openai_router
from .admin import router as admin_router

__all__ = ["openai_router", "admin_router"]

# openwebui_gateway/routes/openai.py

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import uuid

from openwebui_gateway.agent_service import AgentService
from openwebui_gateway.models.schemas import ChatCompletionRequest, ChatCompletionResponse

router = APIRouter(prefix="/v1")
agent_service = AgentService()

@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """OpenAI API compatible chat completions endpoint"""
    
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    
    try:
        if request.stream:
            # Stream response
            async def generate():
                async for chunk in agent_service.chat(
                    x_user_id, 
                    request.messages[-1].content,
                    model=request.model,
                    stream=True
                ):
                    data = {
                        "id": str(uuid.uuid4()),
                        "object": "chat.completion.chunk",
                        "model": request.model,
                        "choices": [{"delta": {"content": chunk}}]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        else:
            # Sync response
            response = agent_service.chat(
                x_user_id,
                request.messages[-1].content,
                model=request.model,
                stream=False
            )
            
            return {
                "id": str(uuid.uuid4()),
                "object": "chat.completion",
                "model": request.model,
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": response
                    },
                    "finish_reason": "stop"
                }]
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_models():
    """List available models"""
    models = agent_service.get_models()
    return {
        "object": "list",
        "data": models
    }

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "cyan-gateway"}
```

```python
# Step 4: Implement main.py
# openwebui_gateway/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openwebui_gateway.routes import openai_router, admin_router

def create_app() -> FastAPI:
    """Create FastAPI app"""
    app = FastAPI(
        title="Cyan Agent Gateway",
        description="OpenAI API compatible backend for Cyan Agent",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers
    app.include_router(openai_router)
    app.include_router(admin_router)
    
    return app

# Global app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18080)
```

```bash
# Step 5: Run tests to verify they pass
python -m pytest tests/openwebui_gateway/test_openai_routes.py -v
# Expected: PASS

# Step 6: Commit
git add openwebui_gateway/routes/ openwebui_gateway/main.py tests/openwebui_gateway/test_openai_routes.py
git commit -m "feat(gateway): implement OpenAI API compatible routes"
```

---

## Task 7: Admin REST API Routes

**Status:** ✅ COMPLETE

**Files:**
- Create: `openwebui_gateway/routes/admin.py`
- Create: `tests/openwebui_gateway/test_admin_routes.py`

```python
# Step 1: Write test for admin endpoints
# tests/openwebui_gateway/test_admin_routes.py

def test_admin_users_list():
    from fastapi.testclient import TestClient
    from openwebui_gateway.main import app
    
    client = TestClient(app)
    
    response = client.get("/api/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

```bash
# Step 2: Run test to verify it fails
python -m pytest tests/openwebui_gateway/test_admin_routes.py::test_admin_users_list -v
# Expected: FAIL
```

```python
# Step 3: Implement admin routes
# openwebui_gateway/routes/admin.py

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List

from openwebui_gateway.session_manager import SessionManager
from openwebui_gateway.profile_service import ProfileService
from openwebui_gateway.tool_service import ToolService

router = APIRouter(prefix="/api/admin")

session_manager = SessionManager()
profile_service = ProfileService()
tool_service = ToolService()

@router.get("/users")
async def list_users():
    """List all users"""
    profiles = profile_service.list_profiles()
    return [
        {
            "user_id": p["user_id"],
            "status": "active",
            "created_at": p["created"],
            "profile_path": p["path"]
        }
        for p in profiles
    ]

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get user details"""
    status = session_manager.get_user_status(user_id)
    return status

@router.get("/users/{user_id}/skills")
async def get_user_skills(user_id: str):
    """Get user skills list"""
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
    """Enable tool (global)"""
    tool_service.enable_tool(tool_name)
    return {"success": True, "message": f"Tool {tool_name} enabled"}

@router.post("/tools/{tool_name}/disable")
async def disable_tool(tool_name: str):
    """Disable tool (global)"""
    tool_service.disable_tool(tool_name)
    return {"success": True, "message": f"Tool {tool_name} disabled"}

@router.get("/tools")
async def list_tools():
    """List all tool status"""
    return tool_service.get_tool_status()

@router.post("/agents/stop/{user_id}")
async def stop_agent(user_id: str):
    """Stop user agent"""
    success = session_manager.stop_agent(user_id)
    return {
        "success": success,
        "message": f"Agent for {user_id} stopped" if success else "Agent not found"
    }

@router.get("/agents/running")
async def list_running_agents():
    """List running agents"""
    return session_manager.list_active_agents()

@router.get("/system/stats")
async def system_stats():
    """System statistics"""
    profiles = profile_service.list_profiles()
    active_agents = session_manager.list_active_agents()
    
    return {
        "total_users": len(profiles),
        "active_agents": len(active_agents),
        "total_tools": len(tool_service.get_tool_status()),
        "enabled_tools": len([t for t in tool_service.get_tool_status() if t["enabled"]])
    }
```

```bash
# Step 4: Run tests to verify they pass
python -m pytest tests/openwebui_gateway/test_admin_routes.py -v
# Expected: PASS

# Step 5: Commit
git add openwebui_gateway/routes/admin.py tests/openwebui_gateway/test_admin_routes.py
git commit -m "feat(gateway): implement admin REST API routes"
```

---

## Task 8: Authentication

**Status:** ✅ COMPLETE

**Files:**
- Create: `openwebui_gateway/auth.py`
- Create: `tests/openwebui_gateway/test_auth.py`

```python
# Step 1: Write test for auth
# tests/openwebui_gateway/test_auth.py

def test_admin_auth():
    from openwebui_gateway.auth import verify_admin_token
    
    import os
    os.environ["ADMIN_SECRET"] = "test_secret"
    
    assert verify_admin_token("test_secret") is True
    assert verify_admin_token("wrong") is False
```

```bash
# Step 2: Run test to verify it fails
python -m pytest tests/openwebui_gateway/test_auth.py::test_admin_auth -v
# Expected: FAIL
```

```python
# Step 3: Implement auth module
# openwebui_gateway/auth.py

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional

# Read admin secret from environment
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "cyan_default_secret")
JWT_ALGORITHM = "HS256"

def create_admin_token(user_id: str) -> str:
    """Create admin JWT token"""
    payload = {
        "user_id": user_id,
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, ADMIN_SECRET, algorithm=JWT_ALGORITHM)

def verify_admin_token(token: str) -> bool:
    """Verify admin token"""
    try:
        payload = jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("role") == "admin"
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False

def get_user_id_from_openwebui_token(token: str) -> Optional[str]:
    """Extract user_id from Open-WebUI token"""
    try:
        payload = jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except:
        return None

def verify_token(token: str) -> Optional[dict]:
    """Generic token verification"""
    try:
        return jwt.decode(token, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        return None
```

```bash
# Step 4: Run tests to verify they pass
python -m pytest tests/openwebui_gateway/test_auth.py -v
# Expected: PASS

# Step 5: Commit
git add openwebui_gateway/auth.py tests/openwebui_gateway/test_auth.py
git commit -m "feat(gateway): implement JWT authentication"
```

---

## Task 9: Admin Dashboard HTML

**Status:** ✅ COMPLETE

**Files:**
- Create: `openwebui_gateway/templates/admin_dashboard.html`

```bash
# Step 1: Create simple admin dashboard
cat > openwebui_gateway/templates/admin_dashboard.html << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cyan Agent Admin</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .stat-card { background: white; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #2196F3; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f0f0f0; }
        button { padding: 5px 10px; margin: 2px; cursor: pointer; }
        .enable { background: #4CAF50; color: white; border: none; }
        .disable { background: #f44336; color: white; border: none; }
        .stop { background: #ff9800; color: white; border: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Cyan Agent Admin</h1>
        
        <div class="card">
            <h2>System Overview</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="total-users">-</div>
                    <div>Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="active-agents">-</div>
                    <div>Active Agents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="enabled-tools">-</div>
                    <div>Enabled Tools</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Tool Management</h2>
            <table id="tools-table">
                <thead>
                    <tr><th>Tool Name</th><th>Description</th><th>Status</th><th>Action</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>Active Users</h2>
            <table id="users-table">
                <thead>
                    <tr><th>User ID</th><th>Status</th><th>Action</th></tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            const res = await fetch('/api/admin/system/stats');
            const data = await res.json();
            document.getElementById('total-users').textContent = data.total_users;
            document.getElementById('active-agents').textContent = data.active_agents;
            document.getElementById('enabled-tools').textContent = data.enabled_tools;
        }
        
        async function loadTools() {
            const res = await fetch('/api/admin/tools');
            const tools = await res.json();
            const tbody = document.querySelector('#tools-table tbody');
            tbody.innerHTML = tools.map(t => `
                <tr>
                    <td>${t.tool_name}</td>
                    <td>${t.description}</td>
                    <td>${t.enabled ? 'Enabled' : 'Disabled'}</td>
                    <td>
                        <button class="${t.enabled ? 'disable' : 'enable'}" 
                                onclick="toggleTool('${t.tool_name}', ${!t.enabled})">
                            ${t.enabled ? 'Disable' : 'Enable'}
                        </button>
                    </td>
                </tr>
            `).join('');
        }
        
        async function loadUsers() {
            const res = await fetch('/api/admin/users');
            const users = await res.json();
            const tbody = document.querySelector('#users-table tbody');
            tbody.innerHTML = users.map(u => `
                <tr>
                    <td>${u.user_id}</td>
                    <td>${u.status}</td>
                    <td><button class="stop" onclick="stopAgent('${u.user_id}')">Stop</button></td>
                </tr>
            `).join('');
        }
        
        async function toggleTool(toolName, enable) {
            await fetch(`/api/admin/tools/${toolName}/${enable ? 'enable' : 'disable'}`, {method: 'POST'});
            loadTools();
        }
        
        async function stopAgent(userId) {
            await fetch(`/api/admin/agents/stop/${userId}`, {method: 'POST'});
            loadUsers();
        }
        
        loadStats();
        loadTools();
        loadUsers();
    </script>
</body>
</html>
EOF
```

```python
# Step 2: Add admin dashboard route
# Add to openwebui_gateway/routes/admin.py

from fastapi import Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

@router.get("/dashboard")
async def admin_dashboard(request: Request):
    """Admin dashboard HTML page"""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})
```

```bash
# Step 3: Commit
git add openwebui_gateway/templates/admin_dashboard.html
git commit -m "feat(gateway): add admin dashboard HTML template"
```

---

## Task 10: Brand Rename (Hermes to Cyan)

**Status:** ✅ COMPLETE

**Files:**
- Modify: `hermes_cli/main.py` (Command registration - add cyan alias)
- Modify: `pyproject.toml` (Package entry points)
- Modify: `hermes_constants.py` (Display functions)
- Modify: `cli.py` (Welcome messages)

```bash
# Step 1: Add cyan command registration via argparse
# hermes_cli/main.py - at module level
```

```python
import sys

def main():
    # Detect invocation name
    invoked_as = sys.argv[0].split('/')[-1].split('\\')[-1]
    is_cyan = invoked_as == 'cyan'
    
    BRAND = "Cyan Agent" if is_cyan else "Hermes Agent"
    
    # Rest of logic unchanged, but use BRAND variable instead of hardcoded "Hermes Agent"
    # ...
```

```toml
# Step 2: Update pyproject.toml entry points
# pyproject.toml

[project.scripts]
hermes = "hermes_cli.main:main"
cyan = "hermes_cli.main:main"  # Same entry point, detects via sys.argv[0]
```

```python
# Step 3: Update hermes_constants.py
# hermes_constants.py

import os
from pathlib import Path

# Read CYAN_HOME first, fallback to HERMES_HOME
CYAN_HOME = os.environ.get("CYAN_HOME", os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
HERMES_HOME = CYAN_HOME  # Backward compatibility

def get_hermes_home() -> Path:
    """Return profile-aware home directory (backward compatible)"""
    return Path(CYAN_HOME)

def display_hermes_home() -> str:
    """User-visible path display (shown as .cyan)"""
    home = Path(CYAN_HOME)
    display_path = str(home)
    # Replace .hermes with .cyan in display only
    return display_path.replace(".hermes", ".cyan")

# New display function for new code
def display_cyan_home() -> str:
    """Cyan brand path display"""
    return display_hermes_home()
```

```python
# Step 4: Update cli.py welcome messages
# cli.py

import sys

invoked_as = sys.argv[0].split('/')[-1].split('\\')[-1]
BRAND_NAME = "Cyan Agent" if invoked_as == 'cyan' else "Hermes Agent"
BRAND_VERSION = "1.0.0"

WELCOME_MESSAGE = f"""Welcome to {BRAND_NAME}!
Type /help for available commands or start chatting.
"""
```

```bash
# Step 5: Global string replacement
# Replace user-visible "Hermes Agent" with dynamic brand detection in:
# - cli.py (help text, messages)
# - hermes_cli/*.py (all user-facing strings)
# Keep technical docs as-is for now

# Step 6: Commit
git add -A
git commit -m "feat(brand): rebrand user-facing strings from Hermes to Cyan"
```

---

## Task 11: Docker & Deployment

**Status:** ✅ COMPLETE

**Files:**
- Create: `Dockerfile.gateway`
- Create: `docker-compose.yaml`
- Modify: `.dockerignore`

```bash
# Step 1: Create Dockerfile for gateway
cat > Dockerfile.gateway << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[all]"
RUN pip install fastapi uvicorn pydantic pyyaml

# Set environment variables
ENV CYAN_HOME=/root/.hermes
ENV PYTHONPATH=/app

# Startup command
CMD ["uvicorn", "openwebui_gateway.main:app", "--host", "0.0.0.0", "--port", "18080"]
EOF
```

```bash
# Step 2: Create docker-compose.yaml
cat > docker-compose.yaml << 'EOF'
version: '3.8'

services:
  cyan-gateway:
    build:
      context: .
      dockerfile: Dockerfile.gateway
    ports:
      - "18080:18080"      # OpenAI API endpoint
    volumes:
      - cyan-data:/root/.hermes
    environment:
      - CYAN_HOME=/root/.hermes
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ADMIN_SECRET=${ADMIN_SECRET:-cyan_default_secret}
      - HERMES_LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18080/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  cyan-cron:
    build:
      context: .
      dockerfile: Dockerfile.gateway
    volumes:
      - cyan-data:/root/.hermes
    environment:
      - CYAN_HOME=/root/.hermes
    command: ["python", "-m", "cron.scheduler"]
    restart: unless-stopped
    depends_on:
      - cyan-gateway

volumes:
  cyan-data:
    driver: local
EOF
```

```bash
# Step 3: Update .dockerignore
cat > .dockerignore << 'EOF'
.env
.venv/
*.egg-info/
__pycache__/
.pytest_cache/
.mypy_cache/
node_modules/
*.log
.DS_Store
.vscode/
.idea/
EOF

# Step 4: Test docker build
docker-compose build
# Expected: Build succeeds without errors

# Step 5: Commit
git add Dockerfile.gateway docker-compose.yaml .dockerignore
git commit -m "feat(deploy): add Docker and docker-compose for gateway"
```

---

## Final Verification Wave

```bash
# F1: Run all tests
python -m pytest tests/openwebui_gateway/ -v --tb=short
# Expected: All tests pass

# F2: Start gateway and test endpoints
# Terminal 1:
python -m uvicorn openwebui_gateway.main:app --host 0.0.0.0 --port 18080 --reload

# Terminal 2: Test health endpoint
curl http://localhost:18080/v1/health

# Terminal 2: Test chat completions
curl -X POST http://localhost:18080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test@company.com" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'

# Terminal 2: Test admin endpoints
curl http://localhost:18080/api/admin/tools
curl http://localhost:18080/api/admin/system/stats

# Expected:
# - Health: {"status": "healthy", "service": "cyan-gateway"}
# - Chat: Returns chat completion JSON
# - Admin: Returns tool list and stats

# F3: Docker compose test
docker-compose up -d
curl http://localhost:18080/v1/health
docker-compose down
# Expected: Gateway starts successfully, health check responds, no errors in logs

# F4: Integration check
# - cyan command works (and hermes still works)
# - User profile auto-creates on first API call
# - Admin dashboard loads at http://localhost:18080/api/admin/dashboard
# - Tool enable/disable affects agent behavior
# - Agent stop terminates running agent
```

---

## Commit Strategy

Each task has its own commit. Final verification commit:

```bash
git add -A
git commit -m "feat(gateway): complete Phase 1 Open-WebUI integration

- FastAPI Gateway with OpenAI API compatibility
- Profile-per-user isolation
- Admin tool control
- Brand rename (hermes to cyan for user-facing)
- Docker deployment support

Tests: pytest tests/openwebui_gateway/ -v"
```

---

## Success Criteria

- [ ] `POST /v1/chat/completions` returns valid OpenAI API format
- [ ] `GET /v1/models` returns model list
- [ ] `GET /v1/health` returns healthy status
- [ ] Admin API: GET /api/admin/users lists profiles
- [ ] Admin API: POST /api/admin/tools/{name}/disable disables tool globally
- [ ] Admin API: POST /api/admin/agents/stop terminates agent (with path param)
- [ ] Profile auto-creates on first request
- [ ] Agent instances are reused across requests (same user)
- [ ] `cyan` command works; user sees "Cyan Agent" branding
- [ ] Docker build succeeds and gateway runs in container
- [ ] All unit tests pass (pytest)

---

**Plan Version**: 1.1 (Clean version)
**Date**: 2026-05-16
**Next Phase**: Phase 2 (Skill approval system + optional code trimming)
