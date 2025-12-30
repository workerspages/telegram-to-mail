
# Telegram to Mail & More - 智能 Telegram 消息转发与管理中心

[![GitHub Actions CI/CD](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml)
[![Docker Image](https://img.shields.io/docker/pulls/workerspages/telegram-to-mail.svg)](https://hub.docker.com/r/workerspages/telegram-to-mail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](README.en.md)** | **[简体中文](README.md)**

一个功能强大、易于部署的 Telegram 自动化工具。它不仅可以实时监听和转发群组消息，还具备**定时任务**、**自动删信**、**消息转发**及**网页爬虫订阅**等功能。

🚀 **最新更新**：新增基于 Bot API 的 **自动删除消息** 和 **消息转发** 功能模块！

项目内置了一个**全新设计**的现代化 Web UI 管理面板，采用极简 SaaS 风格，让所有配置操作都变得优雅且直观。

![Web UI 界面截图](/pic/web.png)

---

## ✨ 核心功能

### 1. 📡 全能监听系统
*   **客户端监听 (Client Mode)**: 登录 TG 账号，实时接收所有加入的群组/频道消息。支持私有群、关键字回复。
*   **网页爬虫订阅 (Scraper Mode)**: **无需登录账号！** 通过监控 `t.me/s/用户名` 官方预览页抓取消息。零风险，适合公开频道广播。

### 2. 🛠️ 群组管理工具 (Bot API) 🆕
*   **自动删除消息**: 设置规则后，Bot 可自动删除指定群组内的消息（支持设置延迟时间）。
    *   *要求：Bot 需加入群组并设为管理员。*
*   **消息转发**: 将一个群组/频道的消息自动转发（Copy）到另一个群组/频道。
    *   *要求：Bot 需同时在源群组和目标群组中。*

### 3. 📨 多通道消息推送
*   **Email**: 支持 SMTP 协议，将监听到的消息发送到您的邮箱。
*   **Bark**: 完美支持 iOS 设备的消息推送。
*   **Pushplus**: 支持微信消息推送，即时触达。

### 4. 🤖 自动化与交互
*   **精细化关键字**: 不同关键字可触发不同通道，支持正则匹配。
*   **自动回复**: 检测到关键字后，可自动在群内回复指定内容（支持设置随机延迟，模拟真人）。
*   **定时任务**: 每日自动发送指令（如 `/checkin` 签到），支持在指定时间段内**随机触发**，规避风控。

### 5. 🖥️ 现代化管理面板
*   **Docker 一键部署**: 开箱即用。
*   **Cloudflare Tunnel 集成**: 可选内置内网穿透，无需公网 IP 也能安全访问后台。

---

## 🚀 快速部署指南

### 先决条件
1.  一台已安装 Docker 的服务器（或 Zeabur/Railway 等容器平台）。
2.  (可选) Telegram `API_ID` 和 `API_HASH`（仅“客户端监听”模式需要，使用 Bot 功能或爬虫模式可不填）。

### 部署步骤

**第一步：克隆本项目**
```bash
git clone https://github.com/workerspages/telegram-to-mail.git
cd telegram-to-mail
```

**第二步：配置 `docker-compose.yml`**
填写必要的环境变量：

```yaml
version: '3.8'
services:
  telegram-to-mail:
    image: ghcr.io/workerspages/telegram-to-mail:aio
    container_name: telegram-to-mail
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - WEB_SECRET_KEY=xxxxxxxxxxxxxxxx     # 保护用户的登录会话
      - WEB_USERNAME=admin
      - WEB_PASSWORD=admin
      
      - API_ID=123456789                    # 可选：如果只用爬虫或Bot功能，可不填
      - API_HASH=123456789abcd              # 可选：如果只用爬虫或Bot功能，可不填

      # 要启用 Cloudflare Tunnel 功能，请取消下面一行的注释，并粘贴您的 Token。
      # 如果此行被注释或值为空，则容器启动时不会启用 Tunnel 功能。
      # Cloudflare Tunnel 域名：https://xxxxxxxxxx-cloudflare-tunnel.com
  #   - TUNNEL_TOKEN=eyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    volumes:
      - ./data:/app/data
    stdin_open: true
    tty: true
    # 日志管理配置
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

```

**第三步：启动服务**

```bash
docker-compose up -d
```

---

## 🔧 功能使用指南

### 1. 自动删除消息 & 消息转发 (Bot 功能) 🆕
> 这些功能依赖 Telegram Bot API，比使用个人账号更稳定且无封号风险。

*   **准备工作**: 在 TG 中向 @BotFather 申请一个 Bot Token。
*   **自动删除**: 
    1. 在 Web 面板点击 **“自动删除消息”** 按钮。
    2. 填写群组 ID、延迟时间（秒）和 Bot Token。
    3. **重要**: 必须将 Bot 拉入该群组并给予“删除消息”的管理员权限。
*   **消息转发**:
    1. 在 Web 面板点击 **“消息转发”** 按钮。
    2. 填写源群组 ID、目标群组 ID 和 Bot Token。
    3. **重要**: Bot 必须能看到源群组的消息（作为成员或管理员），并在目标群组有发言权。

### 2. 网页爬虫订阅 (免登录)
> 适合场景：云服务器部署（无法交互输入验证码）或不想使用自己账号的情况。

*   在 Web 面板点击顶部的 **“订阅”** 按钮。
*   输入公开频道的用户名（例如 `durov`，无需加 @）。
*   勾选通知通道并保存。系统后台会自动轮询更新。

### 3. 客户端监听与自动回复
> 适合场景：私有群组监听、需要以个人账号身份发言/回复。

*   **登录**: 首次启动需查看容器日志输入手机号验证码。
*   **配置**: 点击 **“+ 群组”** 添加监听规则，设置关键字和回复延迟。

### 4. 定时任务 (每日签到)
*   点击 **“🕘 任务”**。
*   设置目标（如 `@bot`）、内容（如 `/checkin`）和时间段（如 `09:00 - 10:00`）。
*   系统将在该时间段内**随机选择一秒**执行，模拟真人操作。

---

## 📂 项目结构

*   `src/telegram-to-mail.py`: 核心后端（包含 Client、Bot API 和 Scraper 逻辑）。
*   `src/web_manager.py`: Flask Web 服务。
*   `src/templates/`: 前端界面。
*   `data/`: 存放配置文件和 Session 会话（建议映射到宿主机）。

---

## 常见问题 (Q&A)

### Q: 使用 Bot 功能需要配置 API_ID 吗？
A: **不需要。** 自动删除和消息转发功能完全基于 Bot Token，与你的个人账号无关。只有当你需要使用“客户端监听”（监听私有群消息并推送到邮箱）或“自动回复”功能时，才需要 API_ID 和登录 Session。

### Q: 使用 Telethon 会不会导致 TG 号被封禁？
A: **Client 模式有风险，Bot 模式无风险。**
*   **Client 模式**: 模拟个人账号操作。如果用于高频群发、拉人，风险极高。本项目已内置随机延迟和防风控机制，正常挂机监听、自动回复、签到通常是安全的，但请使用老号。
*   **Bot / 爬虫模式**: 完全合规，无封号风险。

---
## 📄 许可证
本项目基于 [MIT License](https://opensource.org/licenses/MIT) 授权。
