# 服务器长期运行配置手册

本文档用于把 QQ AI Bot 从本机迁移到云服务器长期运行。当前目标是单 QQ 群灰度，服务器承担 24 小时在线、接收群消息、写入 SQLite、每天 09:00 自动推送昨日群聊总结。

## 当前项目状态

根据当前代码和本地 `.env`，项目已经具备：

- OneBot WebSocket 接收群消息。
- OneBot HTTP `send_group_msg` 发送群消息。
- 火山方舟 OpenAI-compatible Chat Completions 调用。
- Tavily 联网搜索。
- 图片输入理解。
- SQLite 聊天记录持久化。
- 管理员命令。
- 每天 09:00 自动推送昨日群聊总结。

当前 bot 进程没有应用层 WebSocket 自动重连逻辑。如果 OneBot WebSocket 断开，推荐先用 systemd 的 `Restart=always` 做进程级兜底：进程退出后 5 秒重启，相当于粗粒度重连，但不是无感的应用层重连。

仍未完成或暂不进入服务器部署范围：

- 图片生成。
- 语音转文字。
- Web 管理后台。
- 多群配置管理。

## 推荐服务器配置

当前阿里云 ECS 试用实例可以使用：

```text
实例：2 vCPU / 2 GiB
系统盘：ESSD Entry 40 GiB
系统：Ubuntu 22.04 64 位
公网 IP：需要
预装应用：不选
```

2 核 2G 对当前项目足够，因为大模型、搜索和图片理解都走远程 API，本机只跑 Python 服务、SQLite 和 OneBot 协议端。

如果可以重新选择系统，优先选择 Ubuntu 24.04，因为项目要求 Python >= 3.12。若继续使用 Ubuntu 22.04，需要额外安装 Python 3.12。

## 运行架构

服务器上至少常驻两个进程：

```text
QQ 协议端（NapCatQQ 或 Lagrange.OneBot）
  -> 本机 127.0.0.1:3001 WebSocket 上报消息
  -> 本机 127.0.0.1:3000 HTTP 接收发送动作

qq-ai-bot Python 服务
  -> 连接 ws://127.0.0.1:3001
  -> 调用 http://127.0.0.1:3000/send_group_msg
  -> 调用火山方舟 / Tavily 等外部 API
  -> 写入 ./data/bot.sqlite3
```

`3000` 和 `3001` 只允许服务器本机访问，不需要暴露公网。

## 安全组配置

入方向只保留 SSH：

```text
协议：TCP
端口：22
来源：你的本机公网 IP/32
```

应删除或禁用：

```text
RDP 3389  0.0.0.0/0
ICMP 全部 0.0.0.0/0
```

不要开放：

```text
3000
3001
80
443
```

本机公网 IP 可在本机 PowerShell 查询：

```powershell
curl ifconfig.me
```

如果查询结果是 `1.2.3.4`，安全组来源填写：

```text
1.2.3.4/32
```

不要先删除 SSH 规则。先把 SSH 来源从 `0.0.0.0/0` 改成自己的公网 IP，再删除其他规则。

## 服务器初始化

SSH 登录：

```powershell
ssh root@服务器公网IP
```

更新系统并安装基础工具：

```bash
apt update
apt upgrade -y
apt install -y git curl unzip vim ca-certificates software-properties-common
```

## Docker 安装

Docker 用于部署 QQ 协议端。官方 Ubuntu 安装方式是先添加 Docker apt 仓库，再安装 Docker Engine。

卸载可能存在的旧包：

```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do apt-get remove -y $pkg; done
```

添加 Docker 官方仓库：

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
```

安装 Docker Engine 和 Compose 插件：

```bash
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

验证：

```bash
docker --version
docker compose version
docker run --rm hello-world
```

启用开机自启：

```bash
systemctl enable docker
systemctl start docker
```

### Python 3.12

Ubuntu 22.04 默认 Python 版本通常低于 3.12，需要安装 Python 3.12：

```bash
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.12 python3.12-venv python3.12-dev
```

验证：

```bash
python3.12 --version
```

如果 PPA 无法访问，建议改用 Ubuntu 24.04 镜像，或再单独制定 Python 3.12 安装方案。

## 部署项目代码

推荐部署目录：

```text
/opt/qq-ai-bot
```

拉取代码：

```bash
mkdir -p /opt/qq-ai-bot
cd /opt/qq-ai-bot
git clone https://github.com/cesuogaoshou/qq-ai-bot.git .
```

创建虚拟环境并安装：

```bash
python3.12 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
```

验证：

```bash
./.venv/bin/python -m pytest
```

## 配置 `.env`

服务器上的 `.env` 不提交 Git。创建：

```bash
cd /opt/qq-ai-bot
cp .env.example .env
vim .env
```

当前服务器部署建议：

```env
ONEBOT_WS_URL=ws://127.0.0.1:3001
ONEBOT_HTTP_URL=http://127.0.0.1:3000
SQLITE_PATH=./data/bot.sqlite3

BOT_MAX_CONTEXT_MESSAGES=30
BOT_SUMMARY_RECENT_LIMIT=100
BOT_MEMORY_MAX_MESSAGES=5000
BOT_GROUP_COOLDOWN_SECONDS=0
BOT_USER_COOLDOWN_SECONDS=0
BOT_MAX_REPLY_CHARS=300

ENABLE_DAILY_SUMMARY=true
DAILY_SUMMARY_TIME=09:00
DAILY_SUMMARY_LOOKBACK_DAYS=1
DAILY_SUMMARY_MAX_MESSAGES=500

ENABLE_WEB_SEARCH=true
WEB_SEARCH_PROVIDER=tavily
DAILY_SEARCH_LIMIT_PER_GROUP=20
DAILY_SEARCH_LIMIT_PER_USER=5
SEARCH_MAX_RESULTS=3

ENABLE_IMAGE_INPUT=true
IMAGE_INPUT_MODEL=
IMAGE_MAX_BYTES=5242880
DAILY_IMAGE_LIMIT_PER_GROUP=5
DAILY_IMAGE_LIMIT_PER_USER=5
```

以下值从本地 `.env` 手动复制到服务器 `.env`，不要写进文档或提交：

```env
BOT_QQ=
TARGET_GROUP_ID=
BOT_ADMIN_QQ_IDS=
ONEBOT_ACCESS_TOKEN=
LLM_MODEL=
LLM_API_KEY=
TAVILY_API_KEY=
```

## OneBot 协议端

当前项目不自带 QQ 协议端。必须在服务器上另行部署 NapCatQQ 或 Lagrange.OneBot。

协议端需要满足：

```text
WebSocket 上报地址：127.0.0.1:3001
HTTP API 地址：127.0.0.1:3000
access_token：与 .env 的 ONEBOT_ACCESS_TOKEN 一致
登录 QQ：BOT_QQ 对应的机器人账号
```

如果本地已经能跑通某个协议端，服务器优先沿用同一个，减少变量。协议端部署完成前，`qq-ai-bot` 无法接收 QQ 群消息。

### 推荐：NapCat Docker 部署

你本地已经使用过 NapCat，服务器优先沿用 NapCat。NapCat 官方提供 Shell 方式安装，会拉起 Docker 部署流程：

```bash
curl -o napcat.sh https://nclatest.znin.net/NapNeko/NapCat-Installer/main/script/install.sh && sudo bash napcat.sh
```

安装过程中选择 Docker 部署。完成后进入 NapCat WebUI，按页面提示登录机器人 QQ，并配置 OneBot：

```text
HTTP API 监听：0.0.0.0:3000 或 127.0.0.1:3000
WebSocket 监听：0.0.0.0:3001 或 127.0.0.1:3001
access_token：与 qq-ai-bot 的 ONEBOT_ACCESS_TOKEN 一致
```

如果 NapCat 只能监听 `0.0.0.0`，也不要在云安全组开放 `3000/3001`，让端口只在服务器内部使用。

查看 NapCat 容器：

```bash
docker ps
```

查看日志：

```bash
docker logs -f 容器名或容器ID
```

NapCat 跑通后，再启动 `qq-ai-bot`。如果 `/bot ping` 没反应，优先检查：

```text
NapCat 是否已登录机器人 QQ
NapCat 是否加入目标群
OneBot HTTP 端口是否是 3000
OneBot WebSocket 端口是否是 3001
ONEBOT_ACCESS_TOKEN 是否两边一致
安全组是否没有暴露 3000/3001
```

## 手动启动验证

先确保协议端已登录并监听 `3000/3001`，再启动 bot：

```bash
cd /opt/qq-ai-bot
./.venv/bin/qq-ai-bot
```

启动日志应包含：

```text
Starting QQ AI bot
onebot_ws_url=ws://127.0.0.1:3001
onebot_http_url=http://127.0.0.1:3000
access_token=set
llm_api_key=set
Daily summary scheduler enabled
```

群内验证：

```text
/bot ping
/bot status
/bot memory status
@机器人 你好
@机器人 联网搜索今天的热点新闻
@机器人 提取图中文字 + 图片
```

## systemd 常驻服务

协议端跑通后，再把 Python bot 配成 systemd 服务。

当前 bot 依赖 WebSocket 长连接，但代码里还没有应用层断线重连。如果连接断开并导致进程退出，下面的 `Restart=always` 会在 5 秒后重启进程，重新连接 OneBot。它能满足当前长期挂载的基本兜底，但日志里仍可能看到一次断线和重启；后续如需更平滑，再补应用层重连。

创建服务文件：

```bash
vim /etc/systemd/system/qq-ai-bot.service
```

内容：

```ini
[Unit]
Description=QQ AI Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/qq-ai-bot
ExecStart=/opt/qq-ai-bot/.venv/bin/qq-ai-bot
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
systemctl daemon-reload
systemctl enable qq-ai-bot
systemctl start qq-ai-bot
systemctl status qq-ai-bot
```

查看日志：

```bash
journalctl -u qq-ai-bot -f
```

停止：

```bash
systemctl stop qq-ai-bot
```

重启：

```bash
systemctl restart qq-ai-bot
```

## 数据备份

至少备份：

```text
/opt/qq-ai-bot/.env
/opt/qq-ai-bot/data/bot.sqlite3
```

手动备份示例：

```bash
mkdir -p /opt/qq-ai-bot/backups
cp /opt/qq-ai-bot/.env /opt/qq-ai-bot/backups/env.$(date +%F)
cp /opt/qq-ai-bot/data/bot.sqlite3 /opt/qq-ai-bot/backups/bot.$(date +%F).sqlite3
```

试用期结束前必须备份 `.env` 和 `data/bot.sqlite3`，否则释放实例后聊天记忆和密钥配置会丢失。

## 部署检查清单

- ECS 系统为 Ubuntu，公网 IP 可 SSH 登录。
- 安全组只开放 22，且来源限制为自己的公网 IP。
- Python 版本 >= 3.12。
- `/opt/qq-ai-bot` 已拉取 GitHub 仓库。
- `.venv` 创建成功，依赖安装成功。
- `.env` 已填写真实 QQ、群号、管理员、模型 key、搜索 key。
- `SQLITE_PATH=./data/bot.sqlite3`。
- OneBot 协议端已登录机器人 QQ。
- OneBot HTTP 为 `127.0.0.1:3000`。
- OneBot WebSocket 为 `127.0.0.1:3001`。
- `/bot ping` 可回复。
- `/bot status` 显示搜索、图片、限额状态。
- `journalctl -u qq-ai-bot -f` 能看到运行日志。

## 当前待决策

服务器部署前还需要确定一个问题：

```text
协议端选择 NapCatQQ 还是 Lagrange.OneBot？
```

确定后应补充对应协议端的安装、登录、监听端口和 systemd/Docker 常驻配置。
