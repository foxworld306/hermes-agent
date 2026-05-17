# Cyan Agent Phase 1 Learnings

## Conventions
- Use `get_hermes_home()` for all HERMES_HOME paths (from hermes_constants)
- Use `display_hermes_home()` for user-facing messages  
- lazy import `run_agent.AIAgent` to avoid circular deps
- FastAPI routers use `prefix=` for path prefixes
- Admin endpoints use `/api/admin` prefix
- OpenAI endpoints use `/v1` prefix

## Gotchas
- Profile paths must use `_sanitize_user_id` to avoid filesystem issues with special chars
- ToolService uses whitelist pattern (enabled list) - empty = all disabled
- SessionManager uses threading.Lock for lock dict, asyncio.Lock for per-user
- AIAgent __init__ takes ~60 params - read run_agent.py for full signature
- Tests must not write to ~/.hermes/ - use temp dirs

## Decisions
- Port 18080 (uncommon, avoids conflicts)
- CYAN_HOME env var for brand rename (falls back to HERMES_HOME)
- JWT for auth (simple, works for Phase 1)
- Docker: python:3.11-slim base image
- Windows: use `uv venv` + `uv pip install`; pytest addopts has `-n` requiring xdist
- `pytest -o addopts=` overrides pyproject.toml addopts on Windows

## Task 3 Notes
- ToolService whitelist pattern: empty enabled list = ALL tools enabled
- CRITICAL BUG in plan code: `disable_tool` failed when enabled list was empty (all tools enabled by default). Fix: when list is empty, populate it with all tools except the one being disabled
- `enable_tool` just appends to enabled list (works for both empty and non-empty)
- `_ensure_admin_config` creates nested dict structure on first run
- Config path: `admin.tools.enabled` in YAML

## Task 1 Notes
- GatewayConfig uses `dataclasses.dataclass` with defaults
- Pydantic schemas use `BaseModel` with `Literal` for enum-like fields
- Test imports config at runtime to avoid import errors
- Python output capture unreliable on Windows - use direct assertions instead

## Task 4 Notes
- SessionManager lazy-loads `run_agent.AIAgent` via `sys.path.insert` + dynamic import
- AIAgent init wrapped in try/except; falls back to `_StubAIAgent` on failure
- Tests use `@patch.dict("sys.modules", {"run_agent": None})` to force stub path
- Mocking real AIAgent import requires `types.ModuleType("run_agent")` + `patch.dict("sys.modules", ...)`
- `session_manager.py` takes optional `tool_config_path` to isolate ToolService in tests
- Windows: use `.venv\Scripts\python.exe` directly; default `python` alias may be a no-op Store stub
- Test run: `python -m pytest tests/openwebui_gateway/test_session_manager.py -v -o addopts=` — 11 tests pass

## Task 5 Notes
- AgentService wraps SessionManager for all agent interactions
- `_sync_chat` catches all exceptions and returns error string (never raises)
- `_stream_chat` is a TODO placeholder: yields full response as single chunk
- `stop_agent` is a thin delegation to `SessionManager.stop_agent`
- `get_models` returns static OpenAI-format model list for now
- Tests reuse `@patch.dict("sys.modules", {"run_agent": None})` to force stub agent
- `_sync_chat` error handling test temporarily replaces `agent.chat` with a throwing function, then restores it
- Test run: `python -m pytest tests/openwebui_gateway/test_agent_service.py -v -o addopts=` — 5 tests pass

## Task 8 Notes (Auth)
- `openwebui_gateway/auth.py`: JWT auth with PyJWT, HS256, 7-day expiry
- `ADMIN_SECRET` read from env, defaults to `"cyan_default_secret"`
- `verify_admin_token` returns bool; `verify_token` returns payload dict or None
- `get_user_id_from_openwebui_token` extracts `"sub"` claim
- Test uses `importlib.reload` to isolate `ADMIN_SECRET` per test via autouse fixture
- PyJWT 2.12.1 installed via `uv pip install PyJWT`
- Test run: `.\.venv\Scripts\python.exe -m pytest tests/openwebui_gateway/test_auth.py -v -o addopts=` — 18 tests pass
- InsecureKeyLengthWarning from PyJWT is expected with short test secrets; production secrets should be 32+ bytes

## Task 6 Notes (OpenAI API Routes)
- `openwebui_gateway/routes/openai.py`: `/v1/chat/completions`, `/v1/models`, `/v1/health`
- X-User-Id header extraction: `Header(None, alias="X-User-Id")` - returns 401 if missing
- Non-streaming returns OpenAI format: `{id, object, model, choices: [{message, finish_reason}]}`
- Streaming uses `StreamingResponse` with `media_type="text/event-stream"`
- SSE format: `data: {json}\n\n` per chunk, ends with `data: [DONE]\n\n`
- `openwebui_gateway/routes/__init__.py` imports both `openai_router` and `admin_router`
- `openwebui_gateway/routes/admin.py` created early (Task 7 stub) so `__init__.py` imports work
- `openwebui_gateway/main.py`: `create_app()` factory + global `app = create_app()` for uvicorn
- CORS middleware: `allow_origins=["*"]` for Open-WebUI compatibility
- Tests mock `agent_service` at module level: `@patch("openwebui_gateway.routes.openai.agent_service")`
- Streaming test uses async generator mock; verify `text/event-stream` content-type and `[DONE]` sentinel
- fastapi + httpx installed via `uv pip install fastapi httpx`
- Test run: `python -m pytest tests/openwebui_gateway/test_openai_routes.py -v -o addopts=` — 6 tests pass

## Task 7 Notes (Admin REST API Routes)
- `openwebui_gateway/routes/admin.py`: 9 admin endpoints under `/api/admin`
- Endpoints: list users, get user status, get user skills, enable/disable tools, list tools, stop agent, list running agents, system stats
- Services are module-level singletons (`SessionManager()`, `ProfileService()`, `ToolService()`)
- Testing global singletons: use `patch("openwebui_gateway.routes.admin.<service>")` + `importlib.reload(openwebui_gateway.main)` to swap services
- `ProfileService.__init__` creates `profile_base_dir.mkdir(parents=True, exist_ok=True)` — no subdirectories
- `ToolService._ensure_admin_config` writes `admin.tools.enabled: []` to config on first run
- Global `AgentService()` in `routes/openai.py` may create profiles via `SessionManager` — use `>=` assertions for profile counts in tests
- `reload(main_mod)` is needed after patching to re-execute module-level service references in `main.py`
- Test run: 14 tests pass covering all admin endpoints

## Task 11 Notes (Docker & Deployment)
- Existing .dockerignore already had .env, .venv, node_modules, .github, *.md, data/, hermes-config/, runtime/
- Merged plan additions (egg-info, pytest_cache, mypy_cache, *.log, .vscode, .idea, .DS_Store) without losing existing entries
- Dockerfile.gateway: python:3.11-slim, git, pip --no-cache-dir, CYAN_HOME=/root/.hermes, PYTHONPATH=/app, uvicorn on 18080
- docker-compose.yaml: version 3.8, cyan-gateway (port 18080, healthcheck curl /v1/health, cyan-data volume) + cyan-cron (python -m cron.scheduler, same volume)
- API keys passed via env var interpolation (${OPENAI_API_KEY}, ${ADMIN_SECRET:-default}), no hardcoding


## Task 10 Notes (Brand Rename)
- Brand detection via sys.argv[0] split on / and \ at module-level in main.py
- HERMES_BRAND env var set before any hermes module import; downstream modules read this
- hermes_constants.py: _cyan_home module-level reads CYAN_HOME before HERMES_HOME
- get_hermes_home() checks _env_home_override first (CYAN_HOME > HERMES_HOME)
- display_hermes_home() replaces .hermes with .cyan in display when CYAN_HOME set
- get_brand() helper in hermes_constants returns 'cyan' or 'hermes'
- display_cyan_home() is an alias for display_hermes_home()
- cli.py welcome + banner check HERMES_BRAND env var for dynamic fallback strings
- Entry point cyan = 'hermes_cli.main:main' in pyproject.toml shares same main() function
- Skin engine defaults unchanged; brand detection only affects fallback values
