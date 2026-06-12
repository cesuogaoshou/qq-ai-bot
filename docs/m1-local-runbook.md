# M1 本地联调手册

## 目标

本手册用于验证 M1 本地消息闭环：

```text
QQ 测试群
  -> OneBot 协议端
  -> qq-ai-bot
  -> /bot ping
  -> pong
```

M1 只验证收消息、过滤目标群、发送固定回复。不接大模型，不写 SQLite，不做管理员开关。

## 前置条件

需要准备：

- 一个 QQ 小号。
- 一个小测试群，并把 QQ 小号加入群。
- 一个 OneBot 兼容协议端，例如 NapCatQQ 或 Lagrange.OneBot。
- 本项目已完成依赖安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

预期测试结果：

```text
11 passed
```

## 协议端要求

协议端需要暴露两类能力：

- WebSocket 事件地址：机器人后端从这里接收群消息。
- HTTP action 地址：机器人后端通过这里调用 `send_group_msg` 发送群消息。

本项目默认使用：

```text
WebSocket: ws://127.0.0.1:3001
HTTP:      http://127.0.0.1:3000
```

如果你的协议端使用其他端口，以实际配置为准。

## 配置环境变量

在 PowerShell 中设置：

```powershell
$env:ONEBOT_WS_URL="ws://127.0.0.1:3001"
$env:ONEBOT_HTTP_URL="http://127.0.0.1:3000"
$env:ONEBOT_ACCESS_TOKEN=""
$env:TARGET_GROUP_ID="你的测试群号"
```

如果协议端设置了 access token：

```powershell
$env:ONEBOT_ACCESS_TOKEN="你的 token"
```

`TARGET_GROUP_ID` 必须是真实 QQ 群号。M1 会忽略非目标群消息。

## 启动顺序

1. 启动 QQ 协议端。
2. 确认 QQ 小号已登录。
3. 确认协议端已启用 OneBot WebSocket 和 HTTP action。
4. 在项目目录启动机器人：

```powershell
.\.venv\Scripts\qq-ai-bot.exe
```

启动后应看到类似日志：

```text
Starting QQ AI bot: onebot_ws_url=... onebot_http_url=... target_group_id=... access_token=empty
```

日志中不应出现真实 access token。

## 联调步骤

在目标 QQ 群发送：

```text
/bot ping
```

预期机器人回复：

```text
pong
```

验证非目标群过滤：

1. 在另一个群发送 `/bot ping`。
2. 机器人不应回复。

验证非触发消息过滤：

1. 在目标群发送普通消息，例如 `hello`。
2. 机器人不应回复。

## 常见问题

### 启动时报 TARGET_GROUP_ID is required

原因：没有设置 `TARGET_GROUP_ID`。

处理：

```powershell
$env:TARGET_GROUP_ID="你的测试群号"
```

重新启动机器人。

### WebSocket 连接失败

可能原因：

- 协议端没有启动。
- WebSocket 端口不是 `3001`。
- 协议端没有启用 WebSocket 事件服务。
- URL 写成了 HTTP 地址。

检查：

```powershell
$env:ONEBOT_WS_URL
```

确认它是 `ws://...` 开头。

### 收到消息但发送失败

可能原因：

- `ONEBOT_HTTP_URL` 端口不对。
- 协议端没有启用 HTTP action。
- access token 不匹配。
- QQ 小号没有群发言权限。

检查：

```powershell
$env:ONEBOT_HTTP_URL
$env:ONEBOT_ACCESS_TOKEN
```

### 机器人回复了错误的群

原因：`TARGET_GROUP_ID` 配置错了。

处理：

```powershell
$env:TARGET_GROUP_ID="正确的测试群号"
```

重新启动机器人。

### 群里没有回复，但测试通过

测试通过只说明代码逻辑可用，不代表协议端配置正确。按顺序检查：

1. 协议端是否登录 QQ 小号。
2. 小号是否在目标群。
3. WebSocket 地址是否能收到事件。
4. HTTP action 地址是否能发送消息。
5. `TARGET_GROUP_ID` 是否正确。
6. access token 是否一致。

## 完成标准

M1 联调完成需要满足：

- 机器人进程能启动。
- 目标群发送 `/bot ping` 后回复 `pong`。
- 非目标群发送 `/bot ping` 不回复。
- 目标群普通消息不回复。
- access token 不出现在启动日志中。

达到这些标准后，再进入 M2：@ 触发大模型回复。
