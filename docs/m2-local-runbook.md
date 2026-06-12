# M2 本地联调手册

## 目标

本手册用于验证 M2：被 @ 后调用 OpenAI 兼容大模型 API，并把回复发回 QQ 群。

M2 当前能力：

- 继续支持 `/bot ping -> pong`。
- 识别 OneBot CQ 码中的 `@机器人`。
- 读取最近群聊上下文。
- 调用 OpenAI 兼容 `chat/completions` API。
- 限制回复最大长度。
- 大模型超时或失败时不崩溃。

## 前置条件

先完成 M1：

- QQ 小号已登录协议端。
- 目标群 `/bot ping` 能回复 `pong`。
- `ONEBOT_WS_URL` 和 `ONEBOT_HTTP_URL` 已确认可用。

本地测试应通过：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

预期：

```text
41 passed
```

## 环境变量

最小配置：

```powershell
$env:ONEBOT_WS_URL="ws://127.0.0.1:3001"
$env:ONEBOT_HTTP_URL="http://127.0.0.1:3000"
$env:ONEBOT_ACCESS_TOKEN=""
$env:TARGET_GROUP_ID="你的测试群号"
$env:BOT_QQ="机器人 QQ 号"
```

启用大模型回复还需要：

```powershell
$env:LLM_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
$env:LLM_MODEL="doubao-seed-2.0-lite"
$env:LLM_API_KEY="你的 API Key"
```

回复长度和上下文窗口：

```powershell
$env:BOT_MAX_CONTEXT_MESSAGES="30"
$env:BOT_MAX_REPLY_CHARS="300"
```

`LLM_API_KEY` 可以为空。为空时机器人仍能启动并响应 `/bot ping`，但 @ 机器人不会调用大模型。

## 启动

```powershell
.\.venv\Scripts\qq-ai-bot.exe
```

启动日志会显示：

```text
Starting QQ AI bot: ... bot_qq=... llm_model=... access_token=... llm_api_key=...
```

日志只显示 secret 是否设置，不应打印真实 token 或 API key。

## 联调步骤

### 1. 验证 M1 仍可用

在目标群发送：

```text
/bot ping
```

预期：

```text
pong
```

### 2. 验证普通消息不回复

在目标群发送：

```text
今天有人在吗
```

预期：机器人不回复，但这条消息会进入短期上下文。

### 3. 验证 @ 大模型回复

在目标群 @ 机器人并提问：

```text
@机器人 帮我总结一下刚才在聊什么
```

预期：

- 机器人调用大模型。
- 回复发回目标群。
- 回复长度不超过 `BOT_MAX_REPLY_CHARS`。

### 4. 验证非目标群过滤

在非目标群 @ 机器人：

```text
@机器人 你好
```

预期：机器人不回复。

## 常见问题

### @ 了机器人但没有回复

检查：

1. `BOT_QQ` 是否是机器人 QQ 号，不是群号。
2. 协议端上报的消息里是否包含 `[CQ:at,qq=机器人QQ]`。
3. `LLM_API_KEY` 是否已设置。
4. 大模型接口地址和模型名是否正确。

### 启动时报 BOT_QQ is required

原因：没有设置机器人 QQ 号。

处理：

```powershell
$env:BOT_QQ="机器人 QQ 号"
```

### @ 后日志显示 LLM chat failed

可能原因：

- API key 错误。
- `LLM_BASE_URL` 错误。
- `LLM_MODEL` 不存在或无权限。
- 网络不可达。
- 大模型接口不是 OpenAI 兼容格式。

先用同一个 key 和模型在供应商控制台确认可用，再重启机器人。

### 回复太长

调低：

```powershell
$env:BOT_MAX_REPLY_CHARS="160"
```

重启机器人后生效。

## 完成标准

M2 联调完成需要满足：

- `/bot ping` 仍能回复 `pong`。
- 普通目标群消息不触发回复。
- @ 机器人能触发大模型回复。
- 非目标群消息不触发回复。
- API key 不出现在日志中。
- 大模型失败时机器人进程不崩溃。

达到这些标准后，再进入 M3：管理员命令、开关、限频和持久化。
