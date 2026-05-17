# Cyan Agent Phase 1 实施计划 - 待确认问题清单

**创建日期**: 2026-05-16  
**关联计划**: `.sisyphus/plans/cyan-agent-phase1.md` / `.sisyphus/plans/cyan-agent-phase1-zh.md`  
**状态**: 持续更新中

---

## 已识别问题（来自 Prometheus 初始审查）

### 问题 1：认证机制 [待确认] ⭐ HIGH

**描述**: 当前计划使用 `ADMIN_SECRET` 环境变量进行简单 JWT 验证，Open-WebUI 通过 `X-User-Id` header 传递用户身份。

**疑问**:
- Open-WebUI 传给 Gateway 的 `X-User-Id` header 是否足够？还是需要验证 Open-WebUI 的 token？
- 管理员登录 Admin Dashboard 需要独立认证吗？（比如单独的管理员密码）

**建议方案**:
- **第一阶段**: 信任 Open-WebUI 的 SSO 认证，仅使用 `X-User-Id` header 识别用户
- Admin Dashboard 添加简单密码保护（通过 `ADMIN_SECRET`）
- **第二阶段**: 如果需要，可以增加 Open-WebUI token 验证

**决策状态**: 待用户确认

---

### 问题 2：工具列表硬编码 [可接受] ⭐ MEDIUM

**描述**: `_get_all_available_tools()` 返回硬编码列表（`["web_search", "terminal", ...]`）。

**风险**: 如果 Hermes 新增或删除工具，这里需要手动更新。

**建议方案**:
- **第一阶段**: 使用硬编码列表（简单快速）
- **第二阶段**: 从 `toolsets.py` 或 registry 动态扫描工具列表

**决策状态**: Prometheus 建议接受，用户可确认

---

### 问题 3：Admin Dashboard 端口 [待确认] ⭐ MEDIUM

**描述**: 当前计划 Admin Dashboard 和 OpenAI API 使用同一端口（8080），通过 `/api/admin/dashboard` 访问。

**疑问**: 是否需要独立端口（如 8081）？还是同一端口更简洁？

**建议方案**:
- **选项 A（推荐）**: 同一端口（8080），通过路径区分，更简单
- **选项 B**: 独立端口（8081），便于网络层隔离（如内网限制 Admin 访问）

**决策状态**: 待用户确认

---

### 问题 4：AIAgent 初始化参数 [待验证] ⭐ HIGH

**描述**: 计划假设 `AIAgent` 可以接收 `profile_dir` 参数来控制配置文件路径。

**风险**: 实际 `run_agent.py` 中的 `AIAgent.__init__` 可能没有 `profile_dir` 参数。需要确认 Hermes 是否支持按 profile 加载配置。

**建议方案**:
- **首选**: 如果 `AIAgent` 支持 `profile_dir` 参数，直接使用
- **备选**: 在创建 AIAgent 前，临时修改 `os.environ["HERMES_HOME"]` 或 `CYAN_HOME` 指向 profile 目录
- **验证步骤**: 实施 Task 4 时，首先检查 `AIAgent.__init__` 的签名

**决策状态**: 需在实施时验证

---

### 问题 5：依赖管理 [待补充] ⭐ LOW

**描述**: 计划没有明确指定 Gateway 的依赖安装方式。

**缺失依赖**:
- `fastapi`
- `uvicorn`
- `pydantic`（Hermes 已用）
- `pyyaml`（Hermes 已用）
- `jinja2`
- `pyjwt`

**建议方案**:
- 在 `setup.py` 的 extras_require 中添加 `gateway` 选项：
  ```python
  extras_require={
      'gateway': ['fastapi>=0.100.0', 'uvicorn>=0.23.0', 'pyjwt>=2.8.0'],
      # ...
  }
  ```
- 或在项目根目录创建 `requirements-gateway.txt`

**决策状态**: 需在实施时补充

---

### 问题 6：Docker 端口映射 [需要修正] ⭐ LOW

**描述**: `docker-compose.yaml` 映射了 8080 和 8081 两个端口，但如果 Admin Dashboard 和 OpenAI API 在同一端口（8080），8081 映射是多余的。

**修正方案**:
- 如果 Admin 使用同一端口：删除 8081 映射
- 如果 Admin 使用独立端口：确保 FastAPI 应用监听两个端口（需要两个 uvicorn 实例或配置）

**决策状态**: 取决于问题 3 的决策

---

## Momus 审查意见 [已更新]

**审查日期**: 2026-05-16  
**审查结果**: **[REJECT]** - 需要修正 3 个阻塞性问题

**Momus 原文**:
> 网关核心（Tasks 1-6）引用正确且可针对实际代码库执行。然而，Task 10 包含两个框架级不匹配会导致立即失败，Task 7 有一个路由参数 bug 阻止 admin stop-agent 端点运行。

### 阻塞性问题 7：Task 10 使用了 click 框架，但项目使用 argparse [已确认] ⭐ BLOCKER

**描述**: Task 10 品牌重命名代码使用了 `@click.command("cyan")`，但实际的 `hermes_cli/main.py` 使用 `argparse`（第 64 行：`import argparse`），没有使用 `click`。

**影响**: 提供的代码无法编译运行。

**修正方案**:
- 不使用 click，改用 argparse 添加 `cyan` 子命令
- 或在 `main()` 函数入口处检测 `sys.argv[0]`，如果是 `cyan` 则使用 Cyan 品牌显示

**决策状态**: 已确认，需修正计划

---

### 阻塞性问题 8：Task 10 引用了不存在的 setup.py [已确认] ⭐ BLOCKER

**描述**: Task 10 指示修改 `setup.py` 添加 entry points，但项目使用 `pyproject.toml` 进行包配置，不存在顶层 `setup.py`。

**影响**: 无法按指示添加 `cyan` 命令。

**修正方案**:
- 在 `pyproject.toml` 的 `[project.scripts]` 部分添加：
  ```toml
  [project.scripts]
  hermes = "hermes_cli.main:main"
  cyan = "hermes_cli.main:cyan_entry"
  ```

**决策状态**: 已确认，需修正计划

---

### 阻塞性问题 9：Task 7 POST /agents/stop 路由参数错误 [已确认] ⭐ BLOCKER

**描述**: Task 7 的代码：
```python
@router.post("/agents/stop")
async def stop_agent(user_id: str):
```
但路由没有路径参数 `/agents/stop/{user_id}`，也没有从请求体提取。而 Task 9 的 Admin Dashboard HTML 发送 JSON body：`{user_id: userId}`。

**影响**: 端点无法接收 user_id，无法工作。

**修正方案**:
- 方案 A：改为路径参数 `@router.post("/agents/stop/{user_id}")`
- 方案 B：从请求体提取：`async def stop_agent(user_id: str = Body(...))`

**决策状态**: 已确认，需修正计划

---

## 决策记录

| 问题 | 决策 | 日期 | 决策者 |
|------|------|------|--------|
| 问题 1 | 仅使用 X-User-Id header（信任 Open-WebUI SSO） | 2026-05-16 | 用户 |
| 问题 2 | 接受硬编码列表（第一阶段） | 2026-05-16 | Prometheus + 用户 |
| 问题 3 | 同一端口，使用非常见端口（推荐 18080） | 2026-05-16 | 用户 |
| 问题 4 | 实施时验证，备选：临时修改环境变量 | 2026-05-16 | 用户 |
| 问题 5 | 添加依赖到 pyproject.toml | 2026-05-16 | 用户 |
| 问题 6 | 同一端口，使用非常见端口 | 2026-05-16 | 用户 |
| 问题 7 | 使用 argparse + sys.argv[0] 检测 | 2026-05-16 | Momus + 用户 |
| 问题 8 | 修改 pyproject.toml 添加 entry points | 2026-05-16 | Momus + 用户 |
| 问题 9 | 使用路径参数 `/agents/stop/{user_id}` | 2026-05-16 | Momus + 用户 |

---

## 需要修正的内容汇总

基于以上决策，计划文件需要以下修正：

1. ✅ **已修正** - Task 10: 移除 click，改用 argparse + sys.argv[0] 检测
2. ✅ **已修正** - Task 10: 将 setup.py 改为 pyproject.toml
3. ✅ **已修正** - Task 7: `/agents/stop` 改为 `/agents/stop/{user_id}`
4. ✅ **已修正** - 全局端口：8080 → 18080（非常见端口）
5. ✅ **已修正** - 移除 docker-compose.yaml 中的 8081 映射
6. ✅ **已修正** - admin_port 从 8081 移除（与 OpenAI API 共用 18080）

---

## 总结

所有 9 个问题均已确认并修正：
- 3 个阻塞性问题（Momus 发现）已在计划中修正
- 6 个一般问题已得到用户确认

**当前状态**: 计划已可执行

---

## 更新日志

- **2026-05-16**: 初始创建，包含 Prometheus 审查发现的 6 个问题
- **2026-05-16**: Momus 审查发现 3 个阻塞性问题（问题 7-9），已添加
- **2026-05-16**: 用户对全部 9 个问题做出决策，4 项待修正
