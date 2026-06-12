# QQ 群混合型大模型机器人

这是一个面向 QQ 群聊场景的混合型大模型机器人方案。目标不是做一个高频问答助手，而是做一个“轻量群友 + 可控助手”：平时不抢话，被 @ 或明确请求时认真回答，管理员可以控制开关、频率和后续上下文能力。

当前已完成 M1 本地消息闭环、M2 @ 触发大模型回复、M2.5 搜索/安全/成本基础框架、M3 管理员控制，并进入 M4：SQLite 消息持久化、最近聊天总结和记忆清理基础能力已完成。

## 当前结论

推荐采用保守 MVP 路线：

```text
单 QQ 群灰度
  -> OneBot 消息闭环
  -> @ 触发大模型回复
  -> 管理员控制、限频、日志
  -> 关键词和冷场接话体验优化
  -> 多群配置和长期运行优化
```

第一版先支持一个固定群。数据模型和配置结构预留 `group_id`，但不在 MVP 中实现完整多群配置管理。这样可以先验证稳定性、群聊体验和账号风险，再扩展到多个群。

## 技术方向

- QQ 接入：NapCatQQ 或 Lagrange.OneBot。
- 通信协议：OneBot WebSocket 优先，HTTP API 用于发送动作。
- 后端语言：Python 3.12。
- 存储：SQLite。
- 大模型：先接远程 API，后续再考虑本地模型。
- 部署：第一版本机运行，暂不依赖 Docker。

本机环境已确认 Python、pip、Node.js、Git 可用。Docker CLI 存在，但 Docker daemon 当前不可用，因此 Docker 不作为第一版运行方式。

## 文档

- [产品规格书](docs/product-spec.md)：产品定位、MVP 范围、交互策略、成功标准。
- [技术选型设计](docs/technical-selection.md)：关键技术选择、取舍和风险。
- [架构设计](docs/architecture-design.md)：模块边界、数据模型、流程和配置草案。
- [路线图](docs/roadmap.md)：M1 到长期阶段的推进顺序。
- [开发规约](docs/development-guidelines.md)：代码边界、测试、安全、日志和配置约定。
- [高级能力规格](docs/advanced-capabilities-spec.md)：联网搜索、记忆、安全、多模态和成本控制。
- [M1 本地联调手册](docs/m1-local-runbook.md)：OneBot 协议端接入、环境变量、启动和排错步骤。
- [M2 本地联调手册](docs/m2-local-runbook.md)：@ 触发大模型回复、上下文和常见问题。
- [M2.5 本地运行手册](docs/m2-5-local-runbook.md)：搜索触发、安全分级和预算控制。
- [M3 本地运行手册](docs/m3-local-runbook.md)：管理员开关、状态查看、SQLite 和限频验证。
- [M4 本地运行手册](docs/m4-local-runbook.md)：聊天记录持久化、最近总结、记忆状态和清理。

## 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

本地运行前复制 `.env.example` 为 `.env`，并填写 OneBot、大模型和目标群配置。

M1/M2 本地运行：

```powershell
$env:ONEBOT_WS_URL="ws://127.0.0.1:3001"
$env:ONEBOT_HTTP_URL="http://127.0.0.1:3000"
$env:BOT_QQ="机器人 QQ 号"
$env:TARGET_GROUP_ID="你的测试群号"
$env:LLM_API_KEY="你的 API Key"
.\.venv\Scripts\qq-ai-bot.exe
```

在目标群发送 `/bot ping`，预期机器人回复 `pong`。@ 机器人时，如果已配置 `LLM_API_KEY`，会调用大模型生成回复。

M3 管理员命令：

```text
/bot on
/bot off
/bot status
/bot summary recent
/bot memory status
/bot memory clear
/bot summary clear
```

管理员 QQ 号通过 `BOT_ADMIN_QQ_IDS` 配置，多个 QQ 号用英文逗号分隔。

M4 会把目标群内通过安全策略的消息写入 SQLite。隐私或高风险请求不会进入持久化记忆；总结前会对手机号、身份证、银行卡和住址类内容做规则脱敏。

## M2.5 能力状态

当前默认文本模型仍是火山方舟 `doubao-seed-2.0-lite`。

M2.5 增加的是策略层和接口层：

- 安全分级：正常问题继续回答；隐私、高风险和骂战请求会被拦截或降温。
- 搜索触发：识别“搜一下、查一下、最新、今天、现在”等请求。
- 成本控制：搜索按群和用户做每日次数限制。
- 搜索工具：默认关闭，当前使用禁用态客户端，不会真实联网或产生搜索费用。

真实联网搜索供应商需要在确认官方能力、价格和稳定性后接入。

## MVP 成功标准

- 能稳定接收目标群消息。
- 被 @ 后能在合理时间内回复。
- 普通消息默认不触发回复。
- 管理员能开启、关闭和查看状态。
- 每群、每用户限频生效。
- 大模型超时或发送失败时不会导致进程崩溃。
- 日志能定位连接、触发、模型调用和发送失败原因。

## 非 MVP 范围

- 图片理解、语音识别、表情包回复。
- Web 管理后台。
- 多平台接入。
- 复杂插件市场。
- 自动踢人、禁言等群管理动作。
- 长期复杂用户画像。
- 完整多群配置管理。
