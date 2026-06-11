# 技术选型设计

## 总体路线

第一版采用本机 Python 开发版：

```text
NapCatQQ 或 Lagrange.OneBot
  -> OneBot WebSocket
  -> Python 后端
  -> SQLite
  -> 远程大模型 API
```

不建议第一版依赖 Docker。当前本机 Docker CLI 存在，但 Docker daemon 未运行，且存在配置权限告警。Docker 化可以作为长期运行阶段的独立工作。

## QQ 接入

候选：

- NapCatQQ
- Lagrange.OneBot

选择原则：

- 优先支持 OneBot 兼容协议。
- 优先选择本机配置简单、文档清楚、社区反馈稳定的方案。
- MVP 不绑定具体协议端实现，后端只依赖 OneBot 事件和动作接口。

风险：

- 非官方协议端可能触发账号风控。
- 协议端版本变化可能影响事件格式或登录稳定性。

应对：

- 使用小号。
- 先单群低频运行。
- 后端将 OneBot 接入封装在独立模块，避免业务逻辑依赖协议端细节。

## 通信方式

优先使用 OneBot WebSocket 接收事件，使用 OneBot HTTP 或 WebSocket action 发送消息。

原因：

- WebSocket 适合持续接收群消息。
- OneBot action 适合发送群消息、获取必要状态。
- 后端可以保持单一事件循环，便于控制异步流程。

## 后端语言

选择 Python 3.12。

原因：

- 本机已可用。
- 生态适合 WebSocket、SQLite、异步任务和大模型 API 调用。
- 开发速度快，适合先做 MVP。

Node.js 可作为备选，但不是第一优先。PowerShell 下 npm 需要使用 `npm.cmd`，并且当前项目不需要前端工具链。

## 推荐依赖

后续实施时可优先考虑：

- `websockets`：OneBot WebSocket 连接。
- `httpx`：HTTP 请求和大模型 API 调用。
- `pydantic`：配置、事件和领域模型校验。
- `aiosqlite`：异步 SQLite 访问。
- `pytest`：单元测试。

如果后续需要更复杂的数据访问，再评估 SQLAlchemy Core。MVP 不需要 ORM 优先。

## 存储

选择 SQLite。

原因：

- MVP 单机、单群，不需要独立数据库服务。
- 可满足群配置、最近消息、限频状态和日志关联信息存储。
- 迁移到 Postgres 的成本可控，前提是数据访问层边界清楚。

不在 MVP 中引入：

- Postgres
- Redis
- 向量数据库
- 对象存储

## 大模型

第一版接远程 API，不做本地模型。

要求：

- 大模型客户端必须有统一接口。
- 配置中可切换 provider 和 model。
- 必须设置超时。
- 调用失败时返回可控错误，不让主流程崩溃。

接口草案：

```python
class LLMClient:
    async def chat(self, messages: list[dict], *, timeout: float) -> str:
        ...
```

## 配置

配置来源建议分两层：

1. YAML 文件保存非敏感配置。
2. 环境变量保存 API Key、access token 等敏感配置。

配置草案：

```yaml
onebot:
  ws_url: "ws://127.0.0.1:3001"
  access_token_env: "ONEBOT_ACCESS_TOKEN"

llm:
  provider: "openai"
  model: "gpt-4.1-mini"
  api_key_env: "OPENAI_API_KEY"
  timeout_seconds: 20

bot:
  target_group_id: ""
  default_enabled: true
  default_mode: "mention_only"
  max_context_messages: 30
  group_cooldown_seconds: 20
  user_cooldown_seconds: 10
  max_reply_chars: 300

storage:
  sqlite_path: "./data/bot.sqlite3"
```

## 关键取舍

| 方向 | MVP 选择 | 原因 |
| --- | --- | --- |
| 支持群数量 | 单群 | 降低体验和风控风险 |
| 接入方式 | OneBot | 降低 QQ 协议端替换成本 |
| 后端 | Python | 本机可用，开发快 |
| 存储 | SQLite | 单机足够 |
| 模型 | 远程 API | 避免本地模型部署成本 |
| 部署 | 本机运行 | Docker 当前不是阻塞项 |
| 回复模式 | `mention_only` | 最大限度降低刷屏风险 |

## 主要风险

- QQ 账号风控：通过小号、单群、低频降低风险。
- 模型延迟：设置超时，失败时不回复或短回复。
- 成本不可控：限制触发条件、上下文长度和回复频率。
- 隐私风险：只存必要上下文，不做长期画像。
- 代码耦合：OneBot、policy、llm、storage 必须分层。
