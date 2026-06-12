# M3 本地运行手册

## 当前范围

M3 增加可控上线能力：

- 管理员命令：`/bot on`、`/bot off`、`/bot status`
- 管理员 QQ allowlist
- SQLite 保存目标群启用状态
- 群级和用户级基础限频

## 环境变量

```env
BOT_QQ=机器人 QQ 号
TARGET_GROUP_ID=测试群号
BOT_ADMIN_QQ_IDS=管理员QQ号
BOT_GROUP_COOLDOWN_SECONDS=20
BOT_USER_COOLDOWN_SECONDS=10
SQLITE_PATH=./data/bot.sqlite3
```

多个管理员用英文逗号分隔：

```env
BOT_ADMIN_QQ_IDS=111111,222222
```

默认模型保持：

```env
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-seed-2.0-lite
```

## 本地验证

安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

运行：

```powershell
.\.venv\Scripts\qq-ai-bot.exe
```

## 群内验证

管理员发送：

```text
/bot status
/bot off
/bot on
```

预期：

- `/bot status` 返回启用状态、模式、搜索开关和限频。
- `/bot off` 后，普通 @ 不再调用大模型。
- `/bot on` 后，@ 机器人恢复回复。
- 非管理员执行 `/bot on` 或 `/bot off` 会被拒绝。
- 连续 @ 机器人时，命中限频不会再次调用大模型。
