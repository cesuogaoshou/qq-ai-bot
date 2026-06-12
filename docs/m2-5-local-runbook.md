# M2.5 本地运行手册

## 当前范围

M2.5 只上线搜索、安全和成本控制的基础框架：

- 安全策略会拦截隐私、高风险和骂战请求。
- 搜索触发策略会识别需要联网的问题。
- 搜索预算会限制每日搜索次数。
- 搜索客户端默认是禁用态，不会真实联网。

## 环境变量

```env
ENABLE_WEB_SEARCH=false
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

预期：

- 正常问题走 LLM。
- 隐私请求直接拒绝并给替代方向。
- 骂战请求降温。
- 搜索请求在默认关闭时仍走普通 LLM，不产生真实搜索请求。
