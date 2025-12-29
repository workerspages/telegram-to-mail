
# Telegram to Mail & More - 智能 Telegram 消息转发与管理中心

[![GitHub Actions CI/CD](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml)
[![Docker Image](https://img.shields.io/docker/pulls/workerspages/telegram-to-mail.svg)](https://hub.docker.com/r/workerspages/telegram-to-mail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](README.en.md)** | **[简体中文](README.md)**

一个功能强大、易于部署的 Telegram 自动化工具。它不仅可以实时监听和转发群组消息，还具备**定时任务**、**关键字自动回复**、**自动转发**以及**消息自动删除**等高级功能。

🚀 **v2.1 新增功能**：
1. **消息转发 (Forwarding)**: 支持将监听群组的消息自动转发到其他频道/群组（如备份频道）。
2. **自动删除 (Auto-Delete)**: 支持设置消息“阅后即焚”，在指定时间后自动删除，保护隐私或清理记录。

项目内置了一个**全新设计**的现代化 Web UI 管理面板，采用极简 SaaS 风格，让所有配置操作都变得优雅且直观。

![Web UI 界面截图](/pic/web.png)

---

## ✨ 核心功能

### 1. 📡 双模监听系统
*   **客户端监听 (Client Mode)**: 登录 TG 账号，实时接收所有加入的群组/频道消息。支持私有群、关键字回复、转发、删除等高级功能。
*   **网页爬虫订阅 (Scraper Mode)**: **无需登录账号！** 通过监控 `t.me/s/用户名` 官方预览页抓取消息。适合公开频道的匿名监控，绝对零风险。

### 2. 📨 多通道消息推送
*   **Email**: 支持 SMTP 协议，将消息发送到您的邮箱。
*   **Bark**: 完美支持 iOS 设备的消息推送。
*   **Pushplus**: 支持微信消息推送，即时触达。

### 3. 🛠️ 高级消息管理 (🆕)
*   **自动转发**: 将 A 群的消息实时转发到 B 群、C 频道或“收藏夹”。支持配置多个转发目标。
*   **自动删除**: 设置延迟时间（例如 60 秒），系统会在消息发送/接收后自动将其删除。
    *   *注：删除功能受 Telegram 权限限制（如需删除他人消息需要管理员权限，删除自己消息则无需）。*

### 4. 🤖 自动化与交互
*   **精细化关键字**: 不同关键字可触发不同通道。
*   **自动回复**: 检测到关键字后，可自动在群内回复指定内容（支持设置随机延迟，模拟真人）。
*   **定时任务**: 每日自动发送指令（如 `/checkin` 签到），支持在指定时间段内**随机触发**，规避风控。

### 5. 🖥️ 现代化管理面板
*   **Docker 一键部署**: 开箱即用。
*   **Cloudflare Tunnel 集成**: 可选内置内网穿透，无需公网 IP 也能安全访问后台。

---

## 🚀 快速部署指南

### 先决条件
1.  一台已安装 Docker 的服务器（或 Zeabur/Railway 等容器平台）。
2.  (可选) Telegram `API_ID` 和 `API_HASH`（仅“客户端监听”模式需要）。

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
    build: .
    ports:
      - "5000:5000"
    environment:
      - WEB_USERNAME=admin
      - WEB_PASSWORD=admin123
      - API_ID=12345678      # 可选：如果只用爬虫模式，可不填
      - API_HASH=xxxxxxxxx   # 可选：如果只用爬虫模式，可不填
      - TUNNEL_TOKEN=        # 可选：Cloudflare Tunnel Token
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    stdin_open: true
    tty: true
```

**第三步：启动服务**

```bash
docker-compose up -d
```

---

## 🔧 功能使用指南

### 1. 客户端监听与管理 (转发/删除/回复)
> 适合场景：私有群组监听、需要以账号身份发言、备份消息或阅后即焚。

*   **配置**: 登录 Web 面板，点击 **“+ 群组”** 添加监听规则。
*   **自动转发**: 在群组卡片中，找到“自动转发到”区域，点击添加，输入目标频道的用户名（如 `@backup_channel`）或 ID。
*   **自动删除**: 在群组卡片左侧，设置“自动删除消息”的延迟时间（秒）。设置为 `0` 表示关闭此功能。

### 2. 网页爬虫订阅 (免登录)
> 适合场景：云服务器部署（无法交互输入验证码）或不想使用自己账号的情况。

*   在 Web 面板点击顶部的 **“订阅”** 按钮。
*   输入公开频道的用户名（例如 `durov`，无需加 @）。
*   勾选通知通道并保存。系统后台会自动轮询更新。

### 3. 定时任务 (每日签到)
*   点击 **“🕘 任务”**。
*   设置目标（如 `@bot`）、内容（如 `/sign`）和时间段（如 `09:00 - 10:00`）。
*   系统将在该时间段内**随机选择一秒**执行，模拟真人操作。

---

## 📂 项目结构

*   `src/telegram-to-mail.py`: 核心后端（包含 Client 和 Scraper 双线程，处理转发、删除逻辑）。
*   `src/web_manager.py`: Flask Web 服务。
*   `src/templates/`: 前端界面。
*   `data/`: 存放配置文件和 Session 会话（建议映射到宿主机）。

---

## 问：使用 Telethon 会不会导致TG号被封禁？

### 答：**是的，使用 Telethon 有可能导致 TG 账号被封禁，但这主要取决于你“怎么用”，而不是“用了这个库”本身。**

Telethon 是基于 Telegram 官方开放的 MTProto 协议开发的，本身是合规的工具。但是，Telegram 拥有非常严格的反垃圾邮件（Anti-Spam）和反滥用机制。

以下是导致封号的主要原因、风险等级以及防封指南：

### 一、 导致封号的高危行为（千万别做）

1.  **大规模私聊陌生人（最危险）：** 发送垃圾广告几乎必封。
2.  **暴力拉人进群（Force Add）：** 极其危险。
3.  **操作频率过高（非人类速度）：**
    *   本项目在发送、转发消息时已内置了 **随机延时 (Random Sleep)** 机制，模拟人类操作。
    *   **请勿** 将定时任务或转发目标设置得过于密集。

### 二、 如何安全地使用？（防封指南）

1.  **使用老号：** 尽量使用注册时间较长、有正常聊天记录的老账号。
2.  **控制频率：** 脚本内置了防 FloodWait 机制，如果日志提示“Sleeping for X seconds”，请耐心等待，不要重启容器试图绕过。
3.  **合理使用转发：** 不要瞬间将一条消息转发给 100 个群组。

**核心建议：** 把本工具当作一个“不知疲倦的人类助理”，而不是“大规模轰炸机”。只要行为像个正常人，Telegram 就不会管你。

---
## 📄 许可证
本项目基于 [MIT License](https://opensource.org/licenses/MIT) 授权。
