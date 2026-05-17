# Cyan Agent Gateway - 管理员部署与使用手册

> 面向系统管理员 / 运维 / 开发人员的完整操作指南。三步启动：配置 LLM → 启动 Gateway → 连接 Open-WebUI。

---

## 前提检查清单

在开始之前，确认以下事项：

| 检查项 | 状态 | 说明 |
|--------|------|------|
| [ ] Python 3.11+ | 必需 | 推荐使用 `.venv` 虚拟环境 |
| [ ] 内部 LLM 端点就绪 | 必需 | OpenAI 兼容格式，带 `/v1` 后缀 |
| [ ] LLM API Key | 必需 | 即使内部 LLM 通常也需要一个密钥 |
| [ ] 开房端口 18080 | 必需 | Gateway 监听端口 |
| [ ] Hermes Agent 代码 | 必需 | 本仓库代码 |
| [ ] Docker（可选） | 建议生产 | 用于容器化部署 |

### 支持的 LLM 端点类型

Cyan Agent Gateway 必须连接到一个外部 LLM。它使用 **OpenAI 兼容 API 格式**，因此支持：

| 来源 | base_url 示例 | 说明 |
|------|---------------|------|
| **内部 vLLM** | `http://10.0.1.100:8000/v1` | 公司内部部署的 vLLM、TGI、vLLM-4 等 |
| **Ollama** | `http://localhost:11434/v1` | 本地运行 |
| **OpenRouter** | `https://openrouter.ai/api/v1` | 多模型聚合 |
| **NVIDIA NIM** | `https://integrate.api.nvidia.com/v1` | NVIDIA 推理服务 |
| **OpenAI 官方** | `https://api.openai.com/v1` | 默认回退 |
| **Kimi** | `https://api.moonshot.cn/v1` | Moonshot |
| **DeepSeek** | `https://api.deepseek.com/v1` | DeepSeek |

> 内部 LLM 地址必须是以 `/v1` 结尾的 OpenAI 兼容端点。

---

## Step 1：配置 LLM 端点（最重要！）

### 方法 A：环境变量（推荐）

创建环境变量，Gateway 启动时会自动读取：

```bash
# Linux / macOS
export CYAN_BASE_URL="http://你的内部LLM:8000/v1"
export CYAN_API_KEY="your-internal-llm-key"
export CYAN_PROVIDER="openai"
export CYAN_MODEL="gpt-4"
```

```powershell
# Windows PowerShell
$env:CYAN_BASE_URL = "http://10.0.1.100:8000/v1"
$env:CYAN_API_KEY = "your-internal-llm-key"
$env:CYAN_PROVIDER = "openai"
$env:CYAN_MODEL = "gpt-4"
```

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `CYAN_BASE_URL` | **LLM API 基础地址** | `http://10.0.1.100:8000/v1` |
| `CYAN_API_KEY` | **API 密钥** | `internal-key-123` |
| `CYAN_PROVIDER` | 提供商标识 | `openai`（默认） |
| `CYAN_MODEL` | 默认模型 | `gpt-4` |

> **如果你连接的是 OpenAI 官方**，可以省略 `CYAN_BASE_URL`，它会自动使用 `https://api.openai.com/v1`，但 `OPENAI_API_KEY` 仍然需要。

### 方法 B：Docker 环境变量

如果使用 Docker，在 `docker-compose.yaml` 中添加：

```yaml
services:
  cyan-gateway:
    environment:
      - CYAN_BASE_URL=http://内部LLM:8000/v1
      - CYAN_API_KEY=your-internal-llm-key
      - CYAN_PROVIDER=openai
      - CYAN_MODEL=你的模型名
```

### 方法 C：用户配置文件（高级）

每个用户创建个人 `config.yaml`，Gateway 会优先读取：

```yaml
# ~/.hermes/profiles/用户名/config.yaml
model: gpt-4
base_url: http://内部LLM:8000/v1
api_key: your-internal-llm-key
```

### 快速验证 LLM 连接

```bash
curl http://你的内部LLM:8000/v1/models \
  -H "Authorization: Bearer your-internal-llm-key"
```

如果返回模型列表，说明 LLM 端点配置正确。

---

## Step 2：启动 Cyan Agent Gateway

### 方式一：本地运行（开发 / 调试）

```bash
# 1. 进入项目目录
cd hermes-agent

# 2. 激活虚拟环境（如果还没有 venv，先运行：python -m venv .venv）
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\Activate.ps1  # Windows

# 3. 确认依赖
pip install fastapi uvicorn pydantic pyyaml PyJWT

# 4. 设置环境变量（见 Step 1）
export CYAN_BASE_URL="http://10.0.1.100:8000/v1"
export CYAN_API_KEY="your-key"

# 5. 启动 Gateway
uvicorn openwebui_gateway.main:app --host 0.0.0.0 --port 18080 --reload
```

看到以下输出表示启动成功：
```
INFO:     Started server process [xxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:18080 (Press CTRL+C to quit)
```

### 方式二：Docker 运行（生产）

使用 Docker 部署是最简单的方式，把所有步骤放在一起执行。

#### 第一步：创建 docker-compose.yaml

在 `hermes-agent` 目录下创建一个文件，命名为 `docker-compose.yaml`，内容如下（可以直接复制粘贴）：

```yaml
version: '3.8'

services:
  # Cyan Agent Gateway 主服务
  cyan-gateway:
    build:
      context: .                    # 使用当前目录下的代码构建
      dockerfile: Dockerfile.gateway
    ports:
      - "18080:18080"              # 把容器的 18080 端口映射到宿主机的 18080 端口
    volumes:
      - cyan-data:/root/.hermes     # 数据持久化存储（用户档案、会话记录等）
    env_file:
      - .env                        # 从 .env 文件读取环境变量（LLM 地址、密钥等）
    environment:
      - CYAN_HOME=/root/.hermes     # 用户数据存储路径
      - HERMES_LOG_LEVEL=INFO       # 日志级别
    restart: unless-stopped         # 如果崩溃或重启电脑，自动重新启动
    healthcheck:                    # 健康检查：定期确认 Gateway 是否正常工作
      test: ["CMD", "curl", "-f", "http://localhost:18080/v1/health"]
      interval: 30s                 # 每 30 秒检查一次
      timeout: 10s                  # 每次检查最多等 10 秒
      retries: 3                    # 连续 3 次失败才认为不健康

  # 定时任务服务（可选，用于定时执行 Agent 任务）
  cyan-cron:
    build:
      context: .                    # 使用当前目录下的代码构建
      dockerfile: Dockerfile.gateway
    volumes:
      - cyan-data:/root/.hermes     # 和 Gateway 共享同一存储空间
    env_file:
      - .env                        # 从 .env 文件读取环境变量
    environment:
      - CYAN_HOME=/root/.hermes     # 用户数据存储路径
    command: ["python", "-m", "cron.scheduler"]  # 启动定时任务调度器
    restart: unless-stopped         # 自动重启
    depends_on:
      - cyan-gateway                # 确保 Gateway 先启动，再启动 cron

# 持久化存储卷定义
volumes:
  cyan-data:
    driver: local                   # 使用本地存储，数据保存在 Docker 管理的目录中
```

**保存方法**：
- **Windows**：用记事本打开，粘贴上面的内容，选择"文件" → "另存为"，文件名填 `docker-compose.yaml`，保存类型选"所有文件"，保存到 `C:\Projects\hermes-agent` 目录
- **Linux**：在终端运行 `nano docker-compose.yaml`，粘贴内容，按 Ctrl+O，回车，Ctrl+X

#### 第二步：创建 .env 配置文件

在同一个目录下再创建一个 `.env` 文件，内容如下（把等号后面的值换成你自己的）：

```bash
# === LLM 端点配置（必填） ===
CYAN_BASE_URL=http://10.0.1.100:8000/v1
CYAN_API_KEY=你的API密钥
CYAN_PROVIDER=openai
CYAN_MODEL=你的模型名称

# === 管理员密码（建议修改） ===
ADMIN_SECRET=你的管理员密码
```

**常见填写错误**：
- 地址少了 `/v1` 后缀：错误 `http://10.0.1.100:8000`，正确 `http://10.0.1.100:8000/v1`
- 等号两边有空格：错误 `CYAN_BASE_URL = http://...`，正确 `CYAN_BASE_URL=http://...`
- Windows 记事本自动加 `.txt` 后缀：保存时文件名必须是 `.env`，保存类型选"所有文件"

#### 第三步：构建并启动

打开 PowerShell（Windows）或终端（Linux），进入 `hermes-agent` 目录：

```bash
cd hermes-agent   # 或者你自己的路径
docker-compose build    # 构建 Docker 镜像（第一次需要几分钟）
docker-compose up -d    # 后台启动所有服务
```

#### 第四步：查看日志确认启动成功

```bash
docker-compose logs -f cyan-gateway
```

看到以下输出说明启动成功：
```
INFO:     Uvicorn running on http://0.0.0.0:18080 (Press CTRL+C to quit)
```

按 `Ctrl+C` 退出日志查看（不会停止服务）。

#### 第五步：验证运行状态

```bash
docker-compose ps
```

应该看到类似输出：
```
NAME                STATUS
hermes-agent_cyan-gateway_1   Up (healthy)
hermes-agent_cyan-cron_1      Up
```

`STATUS` 显示 `Up` 或 `Up (healthy)` 表示运行正常。

### 验证 Gateway 运行

```bash
# 健康检查
curl http://localhost:18080/v1/health
# {"status": "healthy", "service": "cyan-gateway"}

# 模型列表（如果 LLM 配置正确）
curl http://localhost:18080/v1/models
```

---

## Step 3：连接 Open-WebUI

### 3.1 启动 Open-WebUI

```bash
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

访问 `http://localhost:3000`。

### 3.2 配置连接（图形化步骤）

在 Open-WebUI 界面中：

**路径：设置 → 管理员设置 → 连接 → OpenAI API**

1. 点击 **「添加连接（Add Connection）」**
2. 填写配置：

| 字段 | 值 | 说明 |
|------|-----|------|
| API Endpoint URL | `http://172.17.0.1:18080/v1` | Linux Docker → 宿主机 |
| 或 | `http://host.docker.internal:18080/v1` | Windows/macOS Docker → 宿主机 |
| 或 | `http://localhost:18080/v1` | 两者都在宿主机 |
| API Key | `cyan-local-key` | 任意非空字符串 |

3. **添加自定义请求头（最关键！）**：
   - 点击 **「添加 Header」**
   - Key: `X-User-Id`
   - Value: `{{user_id}}`（动态模板变量，推荐）或固定值如 `admin@company.com`
4. 启用连接，点击保存
5. 刷新页面

### 3.3 网络 URL 对照表

根据你的部署方式选择正确的 URL：

| Open-WebUI 位置 | Gateway 位置 | 使用的 URL |
|----------------|-------------|-----------|
| Docker | 宿主机原生 | `http://172.17.0.1:18080/v1`（Linux）<br>`http://host.docker.internal:18080/v1`（Win/mac） |
| Docker | Docker Compose（同一网络） | `http://cyan-gateway:18080/v1` |
| Docker | Docker Compose（不同网络） | `http://host.docker.internal:18080/v1` |
| 宿主机 | 宿主机 | `http://localhost:18080/v1` |
| 宿主机 | Docker（端口映射） | `http://localhost:18080/v1` |

### 3.4 验证聊天功能

1. 在 Open-WebUI 左上角选择模型（如 `gpt-4`）
2. 发送测试消息："你好"
3. 如果收到回复，说明连接成功
4. 如果返回 401，检查是否配置了 `X-User-Id` 请求头

---

## 管理操作

### 访问管理员仪表盘

浏览器打开：
```
http://localhost:18080/api/admin/dashboard
```

功能：
- **系统概览**：用户数、活跃代理数、工具统计
- **工具管理**：启用/禁用工具（全局生效）
- **用户管理**：查看用户、强制停止代理

### 常用管理 API

```bash
# 系统统计
curl http://localhost:18080/api/admin/system/stats

# 列出所有用户
curl http://localhost:18080/api/admin/users

# 列出工具状态
curl http://localhost:18080/api/admin/tools

# 禁用工具
curl -X POST http://localhost:18080/api/admin/tools/web_search/disable

# 启用工具
curl -X POST http://localhost:18080/api/admin/tools/web_search/enable

# 停止用户代理
curl -X POST http://localhost:18080/api/admin/agents/stop/admin@company.com
```

---

## 故障排查

### 问题 1：Gateway 返回 401 "X-User-Id header required"

**原因**：所有请求必须包含 `X-User-Id` HTTP 头。

**解决**：
```bash
# 测试时加上这个头
curl -H "X-User-Id: test@company.com" http://localhost:18080/v1/chat/completions
```

在 Open-WebUI 中配置自定义请求头（见 Step 3.2）。

### 问题 2：Gateway 启动成功但聊天无响应 / 返回错误

**原因**：LLM 端点配置错误。

**排查步骤**：
```bash
# 1. 检查 LLM 端点是否可达
curl http://你的内部LLM:8000/v1/models

# 2. 检查环境变量是否正确设置
echo $CYAN_BASE_URL
echo $CYAN_API_KEY

# 3. 直接在 Gateway 容器内测试连接
docker exec -it cyan-gateway curl $CYAN_BASE_URL/models
```

### 问题 3：Open-WebUI 无法连接 Gateway

**排查**：
1. 确认 Gateway 端口 `18080` 放行
2. 确认 URL 中的 IP 正确（见 3.3 对照表）
3. 确认 API Key 字段非空

### 问题 4：Docker 中 Gateway 无法访问内部 LLM

**解决**：如果 LLM 在 Docker 外部，使用 `host.docker.internal`：
```yaml
services:
  cyan-gateway:
    environment:
      - CYAN_BASE_URL=http://host.docker.internal:8000/v1
```

如果 LLM 在其他 Docker 容器中，使用 Docker 网络名称：
```yaml
services:
  cyan-gateway:
    environment:
      - CYAN_BASE_URL=http://vllm-server:8000/v1
```

### 问题 5：配置文件保存失败

**原因**：Gateway 需要写入 `~/.hermes/profiles/` 目录。

**解决**：
```bash
# 确保目录可写
chmod 755 ~/.hermes
# 或设置 CYAN_HOME 环境变量
export CYAN_HOME=/writable/path
```

---

## 完整配置示例

### 公司内网部署（推荐生产配置）

```bash
# .env 文件
CYAN_BASE_URL=http://llm-gateway.company.internal:8080/v1
CYAN_API_KEY=internal-llm-secret-key-2024
CYAN_PROVIDER=openai
CYAN_MODEL=Qwen2.5-72B-Instruct
ADMIN_SECRET=admin-dashboard-password
CYAN_HOME=/data/cyan-agent
```

```yaml
# docker-compose.yaml（完整版）
version: '3.8'

services:
  cyan-gateway:
    build:
      context: .
      dockerfile: Dockerfile.gateway
    ports:
      - "18080:18080"
    volumes:
      - cyan-data:/root/.hermes
    env_file:
      - .env
    environment:
      - CYAN_HOME=/root/.hermes
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
    env_file:
      - .env
    environment:
      - CYAN_HOME=/root/.hermes
    command: ["python", "-m", "cron.scheduler"]
    restart: unless-stopped
    depends_on:
      - cyan-gateway

volumes:
  cyan-data:
    driver: local
```

### Ollama 本地部署（个人测试）

```bash
# 1. 启动 Ollama
ollama serve

# 2. 设置环境变量
export CYAN_BASE_URL="http://localhost:11434/v1"
export CYAN_API_KEY="ollama"  # Ollama 通常不需要 key，填任意值
export CYAN_MODEL="llama3.1:8b"

# 3. 启动 Gateway
uvicorn openwebui_gateway.main:app --host 0.0.0.0 --port 18080
```

---

## 验证清单

部署完成后，按照以下清单逐项验证：

- [ ] `curl http://localhost:18080/v1/health` 返回 healthy
- [ ] `curl http://localhost:18080/v1/models` 返回模型列表
- [ ] 带 `X-User-Id` 的请求不返回 401
- [ ] Open-WebUI 中选择模型后能正常聊天
- [ ] 管理员仪表盘能打开
- [ ] 工具启用/禁用生效
- [ ] 用户档案自动创建在 `~/.hermes/profiles/`
- [ ] Docker 日志无持续报错

---

## 下一步

- Phase 1 已完成（Gateway、用户隔离、管理后台）
- Phase 2 计划实现：技能审批系统、代码精简

---

## 附录：服务器部署参考（明天在服务器上执行）

如果你明天需要在服务器上部署，以下是完整步骤：

### 1. 安装 Docker

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证
sudo docker --version
```

### 2. 拉取代码

```bash
# 进入你想存放代码的目录
cd /opt

# 克隆代码（这会下载最新版本，包含今天提交的所有更改）
sudo git clone https://github.com/foxworld306/hermes-agent.git

# 进入项目目录
cd hermes-agent
```

### 3. 创建配置文件

```bash
# 创建 .env 文件
sudo nano .env
```

粘贴以下内容（**等号后面的值改成你自己的**）：

```bash
# === LLM 端点配置（必填） ===
CYAN_BASE_URL=http://你的LLM服务器地址:8000/v1
CYAN_API_KEY=你的API密钥
CYAN_PROVIDER=openai
CYAN_MODEL=你的模型名称

# === 管理员密码（建议修改） ===
ADMIN_SECRET=你的管理员密码
```

**常见填写错误**：
- 地址少了 `/v1` 后缀：错误 `http://10.0.1.100:8000`，正确 `http://10.0.1.100:8000/v1`
- 等号两边有空格：错误 `CYAN_BASE_URL = http://...`，正确 `CYAN_BASE_URL=http://...`

### 4. 启动服务

```bash
# 构建并启动（第一次需要几分钟下载依赖）
sudo docker-compose up -d

# 查看日志确认启动成功（看到 Uvicorn running 说明成功了）
sudo docker-compose logs -f cyan-gateway
```

**按 `Ctrl+C` 退出日志查看（不会停止服务）。**

### 5. 验证

```bash
# 健康检查
sudo curl http://localhost:18080/v1/health

# 查看运行状态
sudo docker-compose ps
```

### 6. 连接 Open-WebUI

在 Open-WebUI 中配置：
- **Base URL**: `http://你的服务器IP:18080/v1`
- **API Key**: 随便填一个非空字符串（如 `cyan-key`）
- **自定义 Header**: `X-User-Id` = `你的用户ID`（如 `admin`）

**参考完整的 Open-WebUI 配置步骤，见本手册 Step 3 部分。**

### 如果出问题

如果启动失败，查看日志：
```bash
sudo docker-compose logs -f cyan-gateway
```

常见问题查看本手册第七部分"故障排查"。

如有问题，查看项目文档 `/website/docs/` 或运行测试：
```bash
# 运行全部 Gateway 测试
pytest tests/openwebui_gateway/ -v -o addopts=
```
