# M5 图片和多模态评估

## 结论

M5 不建议直接进入完整实现。推荐先做“读图输入框架 + 禁用态供应商接口”，图片生成继续后置。

原因：

- 当前默认文本模型保持 `doubao-seed-2.0-lite`，它仍承担普通群聊回复。
- 图片理解、图片生成、图像处理和联网插件在火山方舟文档中是独立能力，需要分别确认模型、调用方式、价格和配额。
- QQ 群图片可能包含个人隐私，第一版不能长期保存原图，也不能把图片内容自动写入记忆。
- 图片生成容易产生额外成本和群聊打扰，必须显式请求、管理员可关、每日限额。

## 官方资料确认点

截至 2026-06-13，火山方舟官方文档可确认：

- 火山方舟文档导航中有“模型列表”和“模型价格”，模型列表页面最近更新时间为 2026-06-12。
- 模型调用下有“多模态理解 / 图片理解”，说明图片理解是独立模型调用能力。
- API 参考中有 Files API、图片生成 API 和兼容 OpenAI SDK 说明。
- 工具调用下有 Web Search 和 Image Process，说明联网搜索与图像处理不应和普通文本聊天混在同一条默认链路。

仍需在接入前从官方控制台或价格页人工确认：

- `doubao-seed-2.0-lite` 是否直接支持图片输入。
- 如果不支持，应该使用哪个火山方舟视觉模型作为 `IMAGE_INPUT_MODEL`。
- 图片输入按 token、图片张数、分辨率还是模型调用计费。
- 图片生成可用模型、单次价格、并发和审核限制。

## 范围拆分

### M5a：读图输入框架

优先级：高。

目标：

- 识别 OneBot 群消息中的图片段。
- 只在用户 @ 机器人并明确要求“看图、解释截图、提取文字、分析图片”时处理图片。
- 图片默认只做短期处理，不写入 SQLite 消息正文，不进入长期记忆。
- 没有启用图片能力或没有配置视觉模型时，返回温和说明，不影响普通文本回复。

建议配置：

```env
ENABLE_IMAGE_INPUT=false
DAILY_IMAGE_LIMIT_PER_GROUP=5
IMAGE_INPUT_MODEL=
IMAGE_MAX_BYTES=5242880
```

### M5b：视觉模型适配器

优先级：中。

目标：

- 增加 `ImageUnderstandingClient` 抽象。
- 默认实现为 disabled client。
- 火山方舟实现只在官方模型能力和价格确认后接入。
- 支持超时、大小限制、调用日志、错误降级。

输出要求：

- 明确说明“根据图片看到的信息回答”。
- 不推断图片中人物身份、隐私、敏感属性。
- 不把图片内容变成用户画像。
- 遇到截图中的账号、手机号、地址、证件号时脱敏或拒绝复述。

### M5c：图片生成

优先级：低，默认后置。

目标：

- 只响应显式“生成图片/画一张图/做表情包草图”。
- 管理员可关闭。
- 每群每日限额。
- 生成结果不自动用于群记忆。

建议配置：

```env
ENABLE_IMAGE_GENERATION=false
DAILY_IMAGE_GENERATION_LIMIT_PER_GROUP=3
IMAGE_GENERATION_MODEL=
```

## 架构设计

推荐数据流：

```text
OneBot group message
  -> message parser
  -> text/image segment extraction
  -> trigger policy
  -> safety policy
  -> image budget policy
  -> image client
  -> LLM reply
  -> output filter
  -> OneBot send group message
```

关键边界：

- `onebot` 层只负责解析图片段和必要的文件/URL 获取。
- `services` 层决定是否处理图片。
- `multimodal` 层负责图片理解、图片生成接口抽象。
- `memory` 层只保存文本摘要，不保存原图。
- `safety` 层继续负责隐私、争吵和高风险内容过滤。

## 风险

- 协议端图片 URL 可能过期，必须尽快拉取或提示用户重发。
- 图片可能很大，必须限制大小和格式。
- 截图里常见个人隐私，不能长期保存原始内容。
- 图片理解模型价格可能高于文本模型，必须限额。
- 图片生成可能带来审核、版权、成本和群聊打扰问题，不能默认开启。

## 下一步建议

先做 M5a 的代码骨架，但仍保持图片能力默认关闭：

1. 给 OneBot 消息解析增加图片段识别测试。
2. 增加图片触发策略测试。
3. 增加 disabled image client。
4. 增加配置读取，但默认关闭。
5. 等官方模型和价格确认后，再接入真实火山方舟视觉模型。

## 参考

- 火山方舟模型列表：https://www.volcengine.com/docs/82379/1330310
- 火山方舟图片理解：https://www.volcengine.com/docs/82379/1362931
- 火山方舟 API 参考：https://www.volcengine.com/docs/82379/1541523
