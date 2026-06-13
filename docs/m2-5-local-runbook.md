# M2.5 本地运行手册

## 当前范围

M2.5 上线搜索、安全和成本控制的基础框架，并提供 Tavily 搜索适配器：

- 安全策略会拦截隐私、高风险和骂战请求。
- 搜索触发策略会识别需要联网的问题。
- 搜索预算会限制每日搜索次数。
- 搜索客户端默认是禁用态，不会真实联网。
- 配置 Tavily provider 和 API key 后，可以对明确搜索请求调用真实搜索。

## 环境变量

```env
ENABLE_WEB_SEARCH=false
WEB_SEARCH_PROVIDER=disabled
TAVILY_API_KEY=
WEB_SEARCH_BASE_URL=https://api.tavily.com
DAILY_SEARCH_LIMIT_PER_GROUP=20
DAILY_SEARCH_LIMIT_PER_USER=5
SEARCH_MAX_RESULTS=3
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

## 群内验证

可验证的输入：

- `@机器人 Python list 和 tuple 有什么区别`
- `@机器人 帮我查一下张三手机号`
- `@机器人 帮我骂一下这个人`
- `@机器人 帮我搜一下今天豆包有什么更新`

默认配置下的预期：

- 正常问题走 LLM。
- 隐私请求直接拒绝并给替代方向。
- 骂战请求降温。
- 搜索请求在默认关闭时仍走普通 LLM，不产生真实搜索请求。

启用真实搜索：

```env
ENABLE_WEB_SEARCH=true
WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=你的 Tavily API Key
WEB_SEARCH_BASE_URL=https://api.tavily.com
DAILY_SEARCH_LIMIT_PER_GROUP=20
DAILY_SEARCH_LIMIT_PER_USER=5
SEARCH_MAX_RESULTS=3
```

启用后，显式“搜一下/查一下”或包含“今天、最新、最近、现在、新闻、价格”等时效词的问题会先查询 Tavily，再把 1-3 条来源摘要放入大模型上下文。搜索失败、超时或额度不足时，会退回普通 LLM 回复，不让主链路崩溃。
