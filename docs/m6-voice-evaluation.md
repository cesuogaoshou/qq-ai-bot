# M6 语音能力评估

## 结论

M6 暂不进入代码实现，先保留为可选能力评估。语音能力的收益明确，但协议端稳定性、转码依赖、语音转文字成本和隐私风险都比读图更高。

推荐结论：

- 第一版不默认启用语音能力。
- 不把语音消息自动转写进长期记忆。
- 只在用户明确要求“转写这段语音/总结这条语音”时考虑处理。
- 先做协议端探针和成本确认，再决定是否进入实现。
- 如果 NapCatQQ 或当前 OneBot 端无法稳定获取语音文件，可以直接放弃 M6。

## OneBot 能力依据

OneBot v11 定义了语音消息段：

```json
{
  "type": "record",
  "data": {
    "file": "http://baidu.com/1.mp3"
  }
}
```

语音段包含 `file`，接收时也可能包含 `url`。OneBot v11 公开 API 还定义了：

- `get_record`：通过收到的语音 `file` 获取并转换语音文件。
- `can_send_record`：检查当前实现是否可以发送语音。

`get_record` 通常需要安装 ffmpeg，且支持转换到 `mp3`、`wav`、`flac` 等格式。因此语音能力不是单纯解析消息段，还依赖协议端实现和本机转码环境。

## 推荐数据流

```text
OneBot group message
  -> record segment extraction
  -> explicit voice trigger policy
  -> voice budget policy
  -> OneBot get_record
  -> local file or URL validation
  -> ASR provider
  -> transcribed text
  -> safety and privacy filter
  -> normal LLM reply
```

## 触发策略

允许触发：

- `@机器人 转写这段语音`
- `@机器人 总结这条语音`
- `@机器人 这段语音说了什么`
- 用户同条消息包含语音，并明确请求处理语音。

不允许触发：

- 普通语音消息自动转写。
- 非 @ 场景自动处理语音。
- 争吵、隐私、人身攻击场景中的语音内容自动总结。
- 把群友语音长期保存为用户画像。

## 配置建议

```env
ENABLE_VOICE_TRANSCRIPTION=false
VOICE_TRANSCRIPTION_PROVIDER=disabled
VOICE_TRANSCRIPTION_MODEL=
DAILY_VOICE_LIMIT_PER_GROUP=3
DAILY_VOICE_LIMIT_PER_USER=1
VOICE_MAX_SECONDS=60
VOICE_MAX_BYTES=10485760
VOICE_RECORD_FORMAT=mp3
```

第一版即使实现，也应保持默认关闭。

## 风险

### 协议端风险

- OneBot 标准有 `record` 消息段和 `get_record` API，但不同实现对文件路径、URL、格式转换和权限的支持可能不同。
- `get_record` 依赖 ffmpeg，Windows 本地运行时需要额外安装并加入 PATH。
- QQ 语音可能是 silk 等格式，ASR 服务未必直接支持。

### 隐私风险

- 群语音包含真实声音和语境，隐私风险高于普通文本。
- 不能默认转写所有语音。
- 不能把转写内容长期写入 SQLite 记忆。
- 如果用户要求总结他人语音，应只做内容级摘要，不推断身份、年龄、性别、情绪病症等敏感属性。

### 成本风险

- ASR 通常按时长或请求计费。
- 群聊里语音可能较长，必须限制时长、文件大小和每日次数。
- 如果 ASR 成本高于当前文本/图片链路，应放弃或只做管理员手动开启。

## 是否进入实现的门槛

满足以下条件才进入 M6a：

1. 当前 OneBot 实现能稳定收到 `record` 段。
2. `record` 段能拿到有效 `file` 或 `url`。
3. `get_record` 能在本机稳定转换到 `mp3` 或 `wav`。
4. 本机 ffmpeg 安装成本可接受。
5. 已确认 ASR 供应商、模型、价格、配额和音频格式。
6. 已明确语音内容不长期存储。

任一关键项不满足，就不进入实现。

## 如果实现，建议拆分

### M6a：协议端探针

- 解析 OneBot `record` 消息段。
- 增加 `/bot voice status` 或日志探针，确认是否收到语音 file/url。
- 调用 `can_send_record` 和 `get_record` 做本地验证。
- 不调用 ASR。

### M6b：ASR 适配器

- 增加 `VoiceTranscriptionClient` 抽象。
- 默认 disabled client。
- 接入一个 ASR provider。
- 增加超时、大小限制、时长限制和成本预算。

### M6c：语音转文本进入普通链路

- 只在明确触发时转写。
- 转写结果先过安全和隐私过滤。
- 作为临时上下文给 LLM，不写入长期记忆。

## 当前建议

暂不写代码。下一步先在真实群里观察当前 OneBot 端收到语音消息时的事件结构，尤其是：

- `message` 里是否包含 `record` 段。
- `record.data.file` 是否稳定。
- `record.data.url` 是否存在。
- `get_record` 是否可用。
- 本机是否已安装 ffmpeg。

拿到真实事件样本后，再决定是否进入 M6a。

## 参考

- OneBot v11 消息段：`record` 语音消息段。https://github.com/botuniverse/onebot-11/blob/master/message/segment.md
- OneBot v11 公开 API：`get_record`、`can_send_record`。https://github.com/botuniverse/onebot-11/blob/master/api/public.md
