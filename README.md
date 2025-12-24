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

## 问：使用 Telethon 会不会导致TG号被封禁？

### 答：**是的，使用 Telethon 有可能导致 TG 账号被封禁，但这主要取决于你“怎么用”，而不是“用了这个库”本身。**

Telethon 是基于 Telegram 官方开放的 MTProto 协议开发的，本身是合规的工具。但是，Telegram 拥有非常严格的反垃圾邮件（Anti-Spam）和反滥用机制。如果你用 Telethon 模拟人工操作时触发了这些风控机制，账号就危险了。

以下是导致封号的主要原因、风险等级以及防封指南：

### 一、 导致封号的高危行为（千万别做）

1.  **大规模私聊陌生人（最危险）：**
    *   如果你写脚本给不在你通讯录里的人群发消息（尤其是带链接的广告），Telegram 会极其迅速地判定你为 Spammer。
    *   **后果：** 即使只发了几十条，如果被接收方点击“Report Spam（举报垃圾消息）”，账号可能瞬间被永封。

2.  **暴力拉人进群（Force Add）：**
    *   使用脚本从一个群抓取成员，然后强制拉入另一个群。
    *   **后果：** 这是 Telegram 打击的重点。轻则账号被限制（不能拉人、不能私聊），重则封号。

3.  **操作频率过高（非人类速度）：**
    *   比如在 1 秒钟内发送 10 条消息，或者瞬间加入 50 个群组。
    *   **后果：** 你的账号会首先遇到 `FloodWaitError`（API 报错，让你等待几十秒到几小时）。如果你无视这个报错，换个 IP 继续猛刷，账号会被系统标记为机器人并封禁。

4.  **新号立即使用 API：**
    *   刚注册的账号（特别是 +86 或虚拟号码如 Google Voice），注册完马上登录 Telethon 进行自动化操作。
    *   **后果：** 这种行为极易被判定为“注册机”生成的账号，导致“秒封”。

### 二、 封禁的类型

1.  **Spam 限制（小黑屋）：**
    *   你无法给陌生人发消息，无法拉人进群，但能在群里说话，能给互存联系人发消息。
    *   可以通过 @SpamBot 查询封禁时长（可能是几天，也可能是永久）。
2.  **账号注销（Ban）：**
    *   打开 App 提示号码被封禁，或者直接被登出，登录时提示 "Phone number is banned"。
    *   这种情况通常很难申诉找回。

### 三、 如何安全地使用 Telethon？（防封指南）

如果你遵循以下规则，使用 Telethon 实际上是**相对安全**的：

1.  **使用老号：**
    *   尽量使用注册时间较长、有正常聊天记录的老账号运行脚本。新号建议先在手机上手动正常使用 1-2 周（俗称“养号”）。

2.  **控制频率（Sleep is your friend）：**
    *   在代码中加入随机的延时。不要循环狂发。
    *   例如：每发送一条消息，`time.sleep(3)` 到 `time.sleep(10)`。
    *   模拟人类的阅读和打字速度。

3.  **正确处理 `FloodWaitError`：**
    *   Telethon 会抛出这个错误，告诉你 Telegram 要求你等待多少秒。
    *   **务必** 捕获这个错误并让脚本休眠相应的时间，绝对不要试图绕过它。

4.  **不要去骚扰陌生人：**
    *   仅对自己加入的群组、自己的收藏夹、或者已经互存联系人的人进行自动化操作。
    *   如果你做 Userbot 仅仅是为了自动回复、自动转发新闻、管理自己的群，通常是非常安全的。

5.  **使用 Session 文件：**
    *   不要每次运行脚本都重新登录（输入验证码）。保存好生成的 `.session` 文件，模拟同一个设备长期在线。

### 总结

*   **如果你用来做：** 自动签到、转发消息到自己的频道、自动回复、清理死粉、群组管理。
    *   **风险：低**（只要频率正常）。
*   **如果你用来做：** 群发广告、暴力拉人、大规模采集数据。
    *   **风险：极高**（几乎必定被封）。

**核心建议：** 把 Telethon 当作一个“不知疲倦的人类助理”，而不是“大规模轰炸机”。只要行为像个正常人，Telegram 就不会管你。

---
## 📄 许可证
本项目基于 [MIT License](https://opensource.org/licenses/MIT) 授权。
