# Telegram to Mail & More - 智能 Telegram 消息转发与管理中心

[![GitHub Actions CI/CD](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml)
[![Docker Image](https://img.shields.io/docker/pulls/workerspages/telegram-to-mail.svg)](https://hub.docker.com/r/workerspages/telegram-to-mail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](README.en.md)** | **[简体中文](README.md)**

一个功能强大、易于部署的 Telegram 自动化工具。它不仅可以实时监听和转发群组消息，还具备**定时任务**、**关键字自动回复**功能。

🚀 **v2.0 新增功能**：引入**网页爬虫（Web Scraper）**技术，支持**免登录、零风险**地订阅公开频道消息！

项目内置了一个**全新设计**的现代化 Web UI 管理面板，采用极简 SaaS 风格，让所有配置操作都变得优雅且直观。

![Web UI 界面截图](/pic/web.png)

---

## ✨ 核心功能

### 1. 📡 双模监听系统
*   **客户端监听 (Client Mode)**: 登录 TG 账号，实时接收所有加入的群组/频道消息。支持私有群、关键字回复等高级功能。
*   **网页爬虫订阅 (Scraper Mode) (🆕)**: **无需登录账号！** 通过监控 `t.me/s/用户名` 官方预览页抓取消息。
    *   **零风险**: 完全匿名访问，绝对不会导致账号被封。
    *   **独立运行**: 即使没有配置 API_ID 或登录 Session，爬虫也能独立工作。

### 2. 📨 多通道消息推送
*   **Email**: 支持 SMTP 协议，将消息发送到您的邮箱。
*   **Bark**: 完美支持 iOS 设备的消息推送。
*   **Pushplus**: 支持微信消息推送，即时触达。

### 3. 🤖 自动化与交互
*   **精细化关键字**: 不同关键字可触发不同通道，支持正则匹配。
*   **自动回复**: 检测到关键字后，可自动在群内回复指定内容（支持设置随机延迟，模拟真人）。
*   **定时任务**: 每日自动发送指令（如 `/checkin` 签到），支持在指定时间段内**随机触发**，规避风控。

### 4. 🖥️ 现代化管理面板
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

### 1. 网页爬虫订阅 (免登录) 🆕
> 适合场景：云服务器部署（无法交互输入验证码）或不想使用自己账号的情况。

*   在 Web 面板点击顶部的 **“订阅”** 按钮。
*   输入公开频道的用户名（例如 `durov`，无需加 @）。
*   勾选通知通道并保存。系统后台会自动轮询更新。

### 2. 客户端监听与自动回复
> 适合场景：私有群组监听、需要以账号身份发言/回复。

*   **登录**: 首次启动需查看容器日志输入手机号验证码。
    *   *注意：如果在 Zeabur 等无法交互的环境，且没有上传 session 文件，系统会自动跳过此模式，仅运行爬虫。*
*   **配置**: 点击 **“+ 群组”** 添加监听规则，设置关键字和回复延迟。

### 3. 定时任务 (每日签到)
*   点击 **“🕘 任务”**。
*   设置目标（如 `@bot`）、内容（如 `/sign`）和时间段（如 `09:00 - 10:00`）。
*   系统将在该时间段内**随机选择一秒**执行，模拟真人操作。

---

## 📂 项目结构

*   `src/telegram-to-mail.py`: 核心后端（包含 Client 和 Scraper 双线程）。
*   `src/web_manager.py`: Flask Web 服务。
*   `src/templates/`: 前端界面。
*   `data/`: 存放配置文件和 Session 会话（建议映射到宿主机）。

## 📄 许可证
本项目基于 [MIT License](https://opensource.org/licenses/MIT) 授权。
