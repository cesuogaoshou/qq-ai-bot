# 架构设计

## 架构目标

MVP 架构优先满足：

- 单群稳定运行。
- 触发规则可控。
- 大模型接入可替换。
- 存储简单可靠。
- 后续可扩展到多群配置。

## 总体架构

```text
QQ 群
  |
  v
QQ 协议端（NapCatQQ / Lagrange.OneBot）
  |
  v
OneBot WebSocket / HTTP
  |
  v
机器人后端（Python）
  |
  +--> onebot      接收事件、发送动作
  +--> router      分发命令和群消息
  +--> policy      判断是否回复
  +--> memory      上下文、配置、限频状态
  +--> llm         大模型调用和提示词
  +--> services    业务流程编排
  |
  v
OneBot 发送群消息
```

## 模块边界

### onebot

职责：

- 建立 WebSocket 连接。
- 接收 OneBot 事件。
- 解析群消息、私聊消息、@ 信息。
- 调用 OneBot action 发送群消息。

不做：

- 不判断是否回复。
- 不拼接提示词。
- 不直接访问业务存储。

### router

职责：

- 管理员命令进入 `command_router`。
- 群消息进入 `message_router`。
- 非目标群消息在 MVP 中直接忽略。
- 无需处理的事件直接丢弃并按需记录调试日志。

### policy

职责：

- 判断机器人是否启用。
- 判断消息是否来自目标群。
- 判断是否被 @。
- 判断是否命中回复模式。
- 判断是否命中限频。
- 判断是否存在明显安全风险。

原则：

```text
policy 只回答“是否回复”和“为什么不回复”，不负责生成回复内容。
```

### memory

职责：

- 保存最近群消息。
- 读取最近上下文。
- 保存机器人开关和模式。
- 保存限频窗口状态。
- 后续支持多群配置。

MVP 只服务一个群，但表结构保留 `group_id`。

### llm

职责：

- 构造模型消息。
- 调用大模型 API。
- 处理超时、失败和空回复。
- 限制最大回复长度。

不做：

- 不决定是否触发。
- 不直接发送群消息。

### services

职责：

- 编排完整业务流程。
- 将 router、policy、memory、llm、onebot 串起来。
- 记录关键日志。

## 核心流程

### 群消息流程

```text
收到 OneBot 群消息
  -> 校验是否目标群
  -> 写入最近消息
  -> 判断是否管理员命令
  -> 判断是否 @ 机器人
  -> 检查开关、模式、限频、安全规则
  -> 读取最近上下文
  -> 构造提示词
  -> 调用大模型
  -> 裁剪或过滤回复
  -> 发送群消息
  -> 写入机器人回复
  -> 记录日志
```

### 管理员命令流程

```text
收到命令
  -> 校验目标群
  -> 校验发送者是否管理员
  -> 解析命令
  -> 修改配置或读取状态
  -> 发送命令结果
  -> 记录日志
```

## 数据模型

### groups

MVP 只有一个群，但仍保留群表，为后续多群配置做准备。

| 字段 | 说明 |
| --- | --- |
| group_id | QQ 群号 |
| enabled | 是否启用 |
| mode | `mention_only` / `quiet` / `active` |
| persona | 群级人设，MVP 可使用默认值 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

### messages

| 字段 | 说明 |
| --- | --- |
| id | 自增 ID |
| group_id | 群号 |
| user_id | 用户 ID |
| nickname | 昵称 |
| role | `user` / `bot` |
| content | 消息内容 |
| created_at | 时间 |

### rate_limits

| 字段 | 说明 |
| --- | --- |
| scope | `group` / `user` |
| scope_id | 群号或用户 ID |
| window_start | 统计窗口开始时间 |
| count | 当前窗口次数 |

### bot_settings

| 字段 | 说明 |
| --- | --- |
| key | 配置键 |
| value | 配置值 |

## 提示词结构

每次模型调用由四部分组成：

```text
系统人设
群配置
最近群聊上下文
当前用户消息
```

示例：

```text
系统：
你是一个 QQ 群里的混合型机器人。平时像群友，被 @ 时像助手。
回复短、自然，不要抢话。争吵时降温。

群配置：
模式：mention_only
风格：轻松、克制、偶尔吐槽

最近上下文：
A：今天好困
B：我也是，开会开麻了

当前消息：
A @机器人：帮我想个下班后恢复状态的方法
```

## 推荐目录结构

后续实施时建议采用：

```text
qq-ai-group-bot/
  README.md
  pyproject.toml
  .env.example
  config/
    default.yaml
  docs/
  src/
    bot/
      __init__.py
      main.py
      config.py
      logging.py
      onebot/
        client.py
        events.py
        actions.py
      router/
        message_router.py
        command_router.py
      policy/
        trigger_policy.py
        rate_limit.py
        safety.py
      llm/
        base.py
        openai_client.py
        prompt_builder.py
      memory/
        context_store.py
        sqlite_store.py
      domain/
        models.py
        group_settings.py
      services/
        chat_service.py
        admin_service.py
  tests/
```

## 多群扩展方式

MVP 不实现完整多群配置，但设计上保留扩展点：

- 所有消息和配置表包含 `group_id`。
- `target_group_id` 先作为单群白名单。
- 后续将单个 `target_group_id` 扩展为 `allowed_group_ids`。
- `groups` 表中每个群独立保存 `enabled`、`mode`、`persona` 和限频参数。
- router 不直接写死群号，而是通过配置或存储判断。

这样可以先用单群降低风险，后续扩展时不需要重写核心架构。
