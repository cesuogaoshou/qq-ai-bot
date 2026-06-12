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
/bot summary recent
/bot memory clear
```

预期：

- `/bot memory status` 返回当前群持久化消息数量。
- `/bot summary recent` 使用最近消息调用大模型总结。
- `/bot memory clear` 清理当前群已保存聊天记录。
- 非管理员执行 M4 管理命令会被拒绝。
