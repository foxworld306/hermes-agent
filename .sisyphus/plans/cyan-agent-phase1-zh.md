# 第一阶段：Cyan Agent Open-WebUI 集成实施计划（中文版）

> **面向执行人员：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实施。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 创建一个 FastAPI 网关，作为 Open-WebUI 的 OpenAI API 兼容后端，使 600+ 企业用户各自拥有独立的 Cyan Agent（通过 Hermes Profile 实现隔离）。

**架构：** 新增 `openwebui_gateway/` 目录，包含 FastAPI 端点、SessionManager（管理每个用户的 Agent 生命周期）、ProfileService（延迟创建 Profile）和 ToolService（管理员全局工具控制）。对现有 Hermes 核心代码的改动最小。

**技术栈：** FastAPI、Pydantic、SSE 流式响应、SQLite、asyncio。复用现有 Hermes：run_agent.py、cli.py、hermes_state.py、model_tools.py。

---

## 文件结构（新增文件）

```
openwebui_gateway/                    # 新增：网关服务
├── __init__.py
├── main.py                           # FastAPI 应用工厂
├── config.py                         # GatewayConfig 数据类
├── auth.py                           # JWT Token 验证、用户提取
├── session_manager.py                # SessionManager：Agent 生命周期
├── profile_service.py                # ProfileService：Profile 增删改查
├── tool_service.py                   # ToolService：全局工具启用/禁用
├── agent_service.py                  # AgentService：AIAgent 包装器
├── models/
│   ├── __init__.py
│   └── schemas.py                    # Pydantic 请求/响应模型
├── routes/
│   ├── __init__.py
│   ├── openai.py                     # /v1/chat/completions, /v1/models, /health
│   └── admin.py                      # /api/admin/* 管理端点
└── templates/
    └── admin_dashboard.html          # 简单的 Jinja2 管理界面

tests/openwebui_gateway/              # 新增：测试套件
├── __init__.py
├── conftest.py
├── test_gateway.py
├── test_session_manager.py
├── test_profile_service.py
└── test_tool_service.py
```

---

## 待办任务列表

### 任务 1：搭建网关模块

**文件：**
- 创建：`openwebui_gateway/__init__.py`
- 创建：`openwebui_gateway/config.py`
- 创建：`openwebui_gateway/models/schemas.py`
- 创建：`tests/openwebui_gateway/__init__.py`

- [ ] **步骤 1：编写 GatewayConfig 的单元测试**

```python
def test_gateway_config_default():
    from openwebui_gateway.config import GatewayConfig
    config = GatewayConfig()
    assert config.host == "0.0.0.0"
    assert config.openai_port == 18080
    assert config.max_concurrent_agents == 50
```

- [ ] **步骤 2：运行测试确认失败**

运行：`python -m pytest tests/openwebui_gateway/test_gateway.py::test_gateway_config_default -v`

预期结果：失败（ModuleNotFoundError 或 ImportError）

- [ ] **步骤 3：实现 GatewayConfig 数据类**

```python
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

- [ ] **步骤 4：实现基础数据模型**

```python
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

- [ ] **步骤 5：运行测试确认通过**

运行：`python -m pytest tests/openwebui_gateway/test_gateway.py -v`

预期结果：通过

- [ ] **步骤 6：提交代码**

```bash
git add openwebui_gateway/ tests/openwebui_gateway/
git commit -m "feat(gateway): 搭建网关模块，包含配置和数据模型"
```

---

### 任务 2：Profile 服务

**文件：**
- 创建：`openwebui_gateway/profile_service.py`
- 修改：`tests/openwebui_gateway/test_profile_service.py`

[详细内容请参考英文版计划文件]

---

### 任务 3：工具服务

**文件：**
- 创建：`openwebui_gateway/tool_service.py`
- 创建：`tests/openwebui_gateway/test_tool_service.py`

[详细内容请参考英文版计划文件]

---

### 任务 4：会话管理器

**文件：**
- 创建：`openwebui_gateway/session_manager.py`
- 创建：`tests/openwebui_gateway/test_session_manager.py`

[详细内容请参考英文版计划文件]

---

### 任务 5：Agent 服务包装器

**文件：**
- 创建：`openwebui_gateway/agent_service.py`
- 创建：`tests/openwebui_gateway/test_agent_service.py`

[详细内容请参考英文版计划文件]

---

### 任务 6：OpenAI API 路由

**文件：**
- 创建：`openwebui_gateway/routes/openai.py`
- 创建：`openwebui_gateway/routes/__init__.py`
- 创建：`tests/openwebui_gateway/test_openai_routes.py`

[详细内容请参考英文版计划文件]

---

### 任务 7：Admin REST API 路由

**文件：**
- 创建：`openwebui_gateway/routes/admin.py`
- 创建：`tests/openwebui_gateway/test_admin_routes.py`

[详细内容请参考英文版计划文件]

---

### 任务 8：认证模块

**文件：**
- 创建：`openwebui_gateway/auth.py`
- 修改：`tests/openwebui_gateway/test_auth.py`

[详细内容请参考英文版计划文件]

---

### 任务 9：Admin 管理后台 HTML

**文件：**
- 创建：`openwebui_gateway/templates/admin_dashboard.html`

[详细内容请参考英文版计划文件]

---

### 任务 10：品牌重命名（Hermes 到 Cyan）

**文件：**
- 修改：`hermes_cli/main.py`（命令注册 - 添加 cyan 别名）
- 修改：`pyproject.toml`（包入口点）
- 修改：`hermes_constants.py`（显示函数）
- 修改：`cli.py`（欢迎消息）

[详细内容请参考英文版计划文件]

---

### 任务 11：Docker 与部署

**文件：**
- 创建：`Dockerfile.gateway`
- 创建：`docker-compose.yaml`
- 修改：`.dockerignore`

[详细内容请参考英文版计划文件]

---

## 最终验证阶段

- [ ] **F1：运行所有测试**

```bash
python -m pytest tests/openwebui_gateway/ -v --tb=short
```

预期结果：所有测试通过

- [ ] **F2：启动网关并测试端点**

```bash
# 终端 1：启动网关
python -m uvicorn openwebui_gateway.main:app --host 0.0.0.0 --port 18080 --reload

# 终端 2：测试健康检查端点
curl http://localhost:18080/v1/health

# 终端 2：测试 Chat Completions
curl -X POST http://localhost:18080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test@company.com" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'

# 终端 2：测试 Admin 端点
curl http://localhost:18080/api/admin/tools
curl http://localhost:18080/api/admin/system/stats
```

预期结果：
- 健康检查：`{"status": "healthy", "service": "cyan-gateway"}`
- 对话：返回 Chat Completion JSON
- Admin：返回工具列表和统计信息

- [ ] **F3：Docker Compose 测试**

```bash
docker-compose up -d
curl http://localhost:18080/v1/health
docker-compose down
```

预期结果：
- 网关在 Docker 中成功启动
- 健康检查端点响应正常
- 日志无错误（`docker-compose logs cyan-gateway`）

- [ ] **F4：集成检查**

验证：
- ✅ `cyan` 命令可用（`hermes` 仍然可用）
- ✅ 首次 API 调用时自动创建用户 Profile
- ✅ 管理后台可在 `http://localhost:18080/api/admin/dashboard` 访问
- ✅ 工具启用/禁用影响 Agent 行为
- ✅ Agent 终止功能正常工作

---

## 提交策略

每个任务独立提交。最终验证提交：

```bash
git add -A
git commit -m "feat(gateway): 完成第一阶段 Open-WebUI 集成

- OpenAI API 兼容的 FastAPI 网关
- 每个用户独立的 Profile 隔离
- 管理员工具控制
- 品牌重命名（hermes 到 cyan，用户可见部分）
- Docker 部署支持

测试：pytest tests/openwebui_gateway/ -v"
```

---

## 成功标准

- [ ] `POST /v1/chat/completions` 返回有效的 OpenAI API 格式
- [ ] `GET /v1/models` 返回模型列表
- [ ] `GET /v1/health` 返回健康状态
- [ ] Admin API：`GET /api/admin/users` 列出所有 Profile
- [ ] Admin API：`POST /api/admin/tools/{name}/disable` 全局禁用工具
- [ ] Admin API：`POST /api/admin/agents/stop` 终止 Agent
- [ ] 首次请求时自动创建 Profile
- [ ] 同一用户的请求复用 Agent 实例
- [ ] `cyan` 命令可用；用户看到 "Cyan Agent" 品牌
- [ ] Docker 构建成功，网关在容器中正常运行
- [ ] 所有单元测试通过（pytest）

---

**计划版本**：1.0  
**日期**：2026-05-16  
**下一阶段**：第二阶段（技能审批系统）

---

**注意**：由于中文编码问题，本文件为简化版。完整的中文详细代码请参考英文版计划文件 `.sisyphus/plans/cyan-agent-phase1.md`。
