
# Telegram to Mail & More - 智能 Telegram 消息转发与管理中心

[![GitHub Actions CI/CD](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml)
[![Docker Image](https://img.shields.io/docker/pulls/workerspages/telegram-to-mail.svg)](https://hub.docker.com/r/workerspages/telegram-to-mail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](README.en.md)** | **[简体中文](README.md)**

一个功能强大、易于部署的 Telegram 自动化工具。它不仅可以实时监听和转发群组消息，还具备**定时任务**、**自动删信**、**消息转发**及**网页爬虫订阅**等功能。

🚀 **最新更新**：
1.  **抽奖自动参与**：检测群组内抽奖信息，自动提取参与关键词并回复参与。
2.  **数据库支持 (MySQL/MariaDB)**：完美适配 Railway/Zeabur 等 PaaS 平台，配置与登录状态云端持久化。
3.  **Bot 增强**：新增基于 Bot API 的自动删除消息和消息转发功能。

项目内置了一个**全新设计**的现代化 Web UI 管理面板，让所有配置操作都变得优雅且直观。

![Web UI 界面截图](/pic/web.png)

---

## ✨ 核心功能

### 1. 📡 全能监听系统
*   **客户端监听 (Client Mode)**: 登录 TG 账号，实时接收所有加入的群组/频道消息。支持私有群、关键字回复。
*   **网页爬虫订阅 (Scraper Mode)**: **无需登录账号！** 通过监控 `t.me/s/用户名` 官方预览页抓取消息。零风险，适合公开频道广播。

### 2. 🛠️ 群组管理工具 (Bot API)
*   **自动删除消息**: 设置规则后，Bot 可自动删除指定群组内的消息（支持设置延迟时间）。
*   **消息转发**: 将一个群组/频道的消息自动转发（Copy）到另一个群组/频道。

### 3. ☁️ 云原生 / PaaS 支持 (NEW)
*   **数据库存储**: 支持连接 MySQL/MariaDB，自动将配置文件和 **Session 登录会话** 存储在数据库中。
*   **无状态容器**: 即使在 Zeabur, Railway 等不提供持久化文件存储的平台上重启，登录状态也不会丢失。
*   **自动切换**: 未配置数据库时，自动降级为本地文件存储 (`./data`)。

### 4. 📨 多通道消息推送
*   **Email**: 支持 SMTP 协议，将监听到的消息发送到您的邮箱。
*   **Bark**: 完美支持 iOS 设备的消息推送。
*   **Pushplus**: 支持微信消息推送，即时触达。

### 5. 🤖 自动化与交互
*   **精细化关键字**: 不同关键字可触发不同通道。
*   **自动回复**: 检测到关键字后，可自动在群内回复指定内容（内置随机延迟，模拟真人）。
*   **定时任务**: 每日在指定时间段内**随机触发**指令（如 `/checkin` 签到），有效规避风控。
*   **抽奖自动参与**: 通过关键词识别抽奖消息，自动提取参与关键词并回复（支持随机延时）。

---

## 🚀 部署指南

### 方式一：Docker Compose (本地/VPS)
适合有持久化存储的传统服务器。

**1. 克隆项目**
```bash
git clone https://github.com/workerspages/telegram-to-mail.git
cd telegram-to-mail
```

**2. 配置启动**
```yaml
version: '3.8'
services:
  telegram-to-mail:
    image: ghcr.io/workerspages/telegram-to-mail:mariadb-lottery
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

      # 可选：通过环境变量传入 Session（适用于不支持文件上传的 PaaS 平台）
      # 值为 session.string 文件内容的 Base64 编码
      # 生成方法: base64 -w 0 session.string
  #   - SESSION_STRING=MUJRQU5PVEUuMTA4...

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
```bash
docker-compose up -d
```

---

### 方式二：PaaS 平台部署 (Koyeb / Zeabur / Railway)
适合免费或低成本的云容器平台，**无需挂载硬盘**。

1.  **部署数据库**: 在您的项目中添加一个 MySQL 或 MariaDB 服务。
2.  **部署本项目**: 添加本项目镜像。
3.  **配置环境变量**:
    填写以下变量以连接数据库：
    *   `MARIADB_HOST`: 数据库地址 (例如 `mysql.railway.internal`)
    *   `MARIADB_PORT`: 端口 (默认 `3306`)
    *   `MARIADB_USER`: 数据库用户名
    *   `MARIADB_PASSWORD`: 数据库密码
    *   `MARIADB_DATABASE`: 数据库名
4.  **配置环境变量**:
    填写以下常用变量：
    *   `WEB_USERNAME`: admin
    *   `WEB_PASSWORD`: admin123
    *   `API_ID`: 12345678          (可选：如果只用爬虫或Bot功能，可不填)
    *   `API_HASH`: xxxxxxxxx       (可选：如果只用爬虫或Bot功能，可不填)
6.  **首次登录**:
    *   部署后查看容器日志（Logs）。
    *   如果配置了 `API_ID`，程序会提示输入手机号和验证码。
    *   **登录成功后，Session 字符串会自动加密存入数据库。**
    *   以后的重启或重新部署将自动读取数据库中的 Session，无需再次验证。





### ✨ 在本地生成 telegram.sessio 文件的方法
[Telegram Session 生成工具及使用方法](/tools/README.md)




#### **上传到 Zeabur**
1.  打开 Zeabur 控制台，找到您的服务。
2.  进入 **Storage（存储）** 选项卡。
3.  找到您挂载的 `/app/data` 目录（或者在项目根目录的 `data` 文件夹）。
4.  将本地生成的 `telegram.session` 上传到 `data/session_data/` 文件夹内（最终路径应为 `/app/data/session_data/telegram.session`）。
5.  **重启服务**。


---

## 🔧 功能使用指南

### 1. 自动删除消息 & 消息转发 (Bot 功能)
> 依赖 Bot API，稳定且无封号风险。

*   **准备**: 向 @BotFather 申请 Bot Token。
*   **配置**: 在 Web 面板点击对应按钮，填写 Token 和群组 ID。
*   **注意**: Bot 必须是群组的管理员（用于删信）或成员（用于转发）。

### 2. 网页爬虫订阅 (免登录)
> 适合场景：云服务器部署（无法交互输入验证码）或不想使用自己账号的情况。

*   在 Web 面板点击 **“订阅”**。
*   输入公开频道用户名（如 `durov`），勾选通知方式即可。

### 3. 客户端监听
> 适合场景：私有群组监听、关键字自动回复。

*   需要配置 `API_ID` 和 `API_HASH` 并登录。
*   支持在 Web 面板添加监听规则、设置关键字回复延迟。

### 4. 定时任务 (每日签到)
*   设置目标（如 `@bot`）、内容（如 `/checkin`）和时间段。
*   系统将在该时间段内**随机选择一秒**执行。

### 5. 抽奖自动参与
> 适合场景：自动参与群组内的抽奖活动。

在群组配置中添加 `lottery` 字段即可启用：
```json
{
  "lottery": {
    "enabled": true,
    "trigger_keywords": ["抽奖信息", "抽奖ID"],
    "reply_delay_min": 3,
    "reply_delay_max": 10
  }
}
```

| 参数 | 说明 |
|------|------|
| `enabled` | 是否启用 |
| `trigger_keywords` | 识别抽奖消息的关键词列表 |
| `reply_delay_min` | 回复最小延时（秒） |
| `reply_delay_max` | 回复最大延时（秒） |

---

## 📂 项目结构

*   `src/storage.py`: **(核心)** 数据存储层，自动判断使用本地文件还是数据库。
*   `src/telegram-to-mail.py`: 核心业务逻辑（Client / Bot / Scraper）。
*   `src/web_manager.py`: Flask Web 面板。
*   `data/`: 本地模式下的数据存储目录。

---

## 常见问题 (Q&A)

### Q: 部署到 Koyeb / Zeabur / Railway 后，重启容器配置丢失了？
A: 请确保您配置了 `MARIADB_` 系列环境变量。如果配置正确，程序日志会显示 `[Storage] Using MariaDB mode`，此时配置会存入数据库，重启不会丢失。如果不配置数据库，PaaS 平台的临时文件系统会在重启后重置。

### Q: 使用 Bot 功能需要配置 API_ID 吗？
A: **不需要。** 自动删除和消息转发功能仅依赖 Bot Token。只有当您需要“客户端监听”（用个人号监听私有群）或“自动回复”时才需要 API_ID。

---
## 📄 许可证
本项目基于 [MIT License](https://opensource.org/licenses/MIT) 授权。
