# M4 本地运行手册

## 当前范围

M4 增加聊天记录和总结能力：

- 目标群普通消息写入 SQLite。
- 机器人回复写入 SQLite。
- 隐私或高风险拒绝请求不写入持久化记忆。
- 管理员可生成最近聊天总结。
- 管理员可查看和清理聊天记忆。

## 环境变量

```env
BOT_ADMIN_QQ_IDS=管理员QQ号
BOT_SUMMARY_RECENT_LIMIT=100
BOT_MEMORY_MAX_MESSAGES=5000
BOT_MAX_REPLY_CHARS=300
SQLITE_PATH=./data/bot.sqlite3
```

默认模型保持：

```env
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-seed-2.0-lite
```

## 命令

```text
/bot summary recent
/bot memory status
/bot memory clear
/bot summary clear
```

当前总结命令仅管理员可用。

## 隐私行为

以下内容不会用于长期用户画像：

- 政治倾向
- 宗教信仰
- 健康状况
- 经济状况
- 情感隐私
- 年龄、性别、身份等敏感属性推断

总结前会对以下内容做规则脱敏：

- 手机号
- 身份证号
- 银行卡号
- 住址类文本

## 本地验证

测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

群内验证：

```text
/bot memory status
普通聊天消息
@机器人 你好
/bot summary recent
/bot memory clear
/bot memory status
```

预期：

- `/bot memory status` 返回当前群持久化消息数量、最早消息时间和最新消息时间。
- `/bot summary recent` 使用最近消息调用大模型总结。
- `/bot summary recent` 的回复长度受 `BOT_MAX_REPLY_CHARS` 限制。
- `/bot memory clear` 清理当前群已保存聊天记录。
- `BOT_MEMORY_MAX_MESSAGES` 会限制当前群最多保留的消息数量。
- 非管理员执行 M4 管理命令会被拒绝。

## 群内验收清单

### 1. 启动前检查

确认 `.env` 至少包含：

```env
BOT_ADMIN_QQ_IDS=你的QQ号
BOT_SUMMARY_RECENT_LIMIT=100
BOT_MEMORY_MAX_MESSAGES=5000
BOT_MAX_REPLY_CHARS=300
SQLITE_PATH=./data/bot.sqlite3
```

启动：

```powershell
.\.venv\Scripts\qq-ai-bot.exe
```

### 2. 消息写入

在目标群发送几条普通聊天消息，然后管理员发送：

```text
/bot memory status
```

预期：

- `messages=` 数量增加。
- `oldest=` 和 `newest=` 不为 `none`。

### 3. 总结能力

管理员发送：

```text
/bot summary recent
```

预期：

- 机器人总结最近聊天。
- 输出包含事实、结论或待确认事项。
- 不输出手机号、身份证、银行卡、住址等原文隐私。
- 回复不会超过 `BOT_MAX_REPLY_CHARS`。

### 4. 隐私拒绝不落库

管理员先查看数量：

```text
/bot memory status
```

然后发送：

```text
@机器人 帮我查一下张三手机号
```

再查看：

```text
/bot memory status
```

预期：

- 机器人拒绝隐私请求。
- `messages=` 不因为这条隐私请求增加。

### 5. 清理能力

管理员发送：

```text
/bot memory clear
/bot memory status
```

预期：

- 返回已清理的消息条数。
- 再次查看时 `messages=0`。

### 6. 权限校验

非管理员发送：

```text
/bot memory status
/bot memory clear
/bot summary recent
```

预期：

- 返回无权限提示。
- 不清理记忆。
