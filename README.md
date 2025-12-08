
# Telegram to Mail & More - 智能 Telegram 消息转发与管理中心

[![GitHub Actions CI/CD](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml)
[![Docker Image](https://img.shields.io/docker/pulls/workerspages/telegram-to-mail.svg)](https://hub.docker.com/r/workerspages/telegram-to-mail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](README.en.md)** | **[简体中文](README.md)**

一个功能强大、易于部署的 Telegram 自动化工具。它不仅可以实时监听和转发群组消息，还具备**定时任务（如自动签到）**和**关键字自动回复**功能，是您管理 Telegram 消息的得力助手。

项目内置了一个**全新设计**的现代化 Web UI 管理面板，采用极简 SaaS 风格，让所有配置操作都变得优雅且直观。

![Web UI 界面截图](/pic/web.png) ---

## ✨ 核心功能

* **实时群组监听**: 基于 Telethon 库，稳定、高效地接收指定 Telegram 群组的新消息。
* **多通道消息推送**:
    * **Email**: 支持 SMTP 协议，将消息发送到您的邮箱。
    * **Bark**: 完美支持 iOS 设备的消息推送。
    * **Pushplus**: 支持微信消息推送，即时触达。
* **精细化关键字规则**:
    * **精准转发**: 不同的关键字可触发不同的推送通道。
    * **自动回复**: 🆕 检测到关键字后，可自动在群组内回复指定内容。
    * **自定义延迟**: 🆕 支持设置回复的延迟时间（秒），模拟真人操作。
* **定时发送任务 (🆕)**:
    * **每日签到**: 每天向指定的机器人或群组发送指令（如 `/checkin`）。
    * **随机时间段**: 🆕 支持设置“开始时间”与“结束时间”，系统将在区间内**随机选择一秒**发送，有效规避 Telegram 风控，防止封号。
* **现代化 Web UI (🆕)**:
    * **全新设计**: 采用玻璃拟态（Glassmorphism）与卡片式设计，视觉体验大幅提升。
    * **交互优化**: 使用现代化开关（Toggle）替代传统复选框，操作更顺手。
    * **即时保存**: 所有修改自动同步，无需手动保存。
* **容器化与零配置**:
    * Docker 一键部署，开箱即用。
    * 可选 Cloudflare Tunnel 集成，无需公网 IP 也能安全访问后台。


## 🚀 快速部署指南

### 先决条件

1.  一台已安装 [Docker](https://www.docker.com/) 和 [Docker Compose](https://docs.docker.com/compose/install/) 的服务器。
2.  一个 Telegram 账号，并已从 [my.telegram.org](https://my.telegram.org) 获取到 `API_ID` 和 `API_HASH`。

### 部署步骤

**第一步：克隆本项目**
```bash
git clone [https://github.com/workerspages/telegram-to-mail.git](https://github.com/workerspages/telegram-to-mail.git)
cd telegram-to-mail
````

**第二步：配置 `docker-compose.yml`**

打开项目根目录下的 `docker-compose.yml` 文件，填写必要的环境变量：

```yaml
services:
  telegram-to-mail:
    build: .
    # ...
    environment:
      # --- 必填配置 ---
      - WEB_USERNAME=admin                              # 设置您的后台登录用户名
      - WEB_PASSWORD=your_strong_password             # 设置您的后台登录密码
      - API_ID=12345678                                 # 填入您的 Telegram API_ID
      - API_HASH=your_telegram_api_hash                 # 填入您的 Telegram API_HASH
      - WEB_SECRET_KEY=generate_a_long_random_string    # ★ 务必修改为一个长且随机的字符串，用于加密 session

      # --- 选填：Cloudflare Tunnel ---
      # 如需启用，请取消注释并填入您的 Token。留空则不启用。
      - TUNNEL_TOKEN=
```

**第三步：启动服务**

```bash
docker-compose build
docker-compose up -d
```

**第四步：首次登录授权**

1.  访问 Web UI：`http://<服务器IP>:5000`。
2.  首次启动需进行 Telegram 登录授权。请查看容器日志：
    ```bash
    docker-compose logs -f
    ```
    根据日志提示输入手机号和验证码即可。

-----

## 🔧 功能使用指南

### 1\. 消息监听与自动回复

  * 点击右上角“**+ 群组**”添加监听规则。
  * **关键字转发**: 输入关键字并勾选 Bark/Email 等通道，命中后即刻推送。
  * **自动回复**: 在关键字规则中，您可以填写“自动回复内容”以及“延迟时间（秒）”。系统会在检测到关键字后，等待指定秒数再回复，显得更加自然。

### 2\. 定时任务 (每日签到)

  * 点击页面顶部的“**🕘 任务**”按钮。
  * **目标**: 填写机器人用户名（如 `@sheeridverifier_bot`）或群组 ID。
  * **发送内容**: 填写签到指令（如 `/checkin`）。
  * **随机触发时段**: 设置一个较宽的时间窗口（例如 `09:00` - `10:00`）。系统每天会在此区间内**随机**选择一个时间点发送消息，极大降低被判定为机器人的风险。

### 3\. 推送通道管理

  * 点击右上角**齿轮图标**⚙️。
  * 支持配置无限个 Bark 设备和 Pushplus 账号，并为它们分别命名（ID），方便在不同群组中灵活调用。

-----

## 🛠️ 项目结构

  * `src/telegram-to-mail.py`: 核心后端，负责 Telegram 协议交互、消息监听、定时任务调度。
  * `src/web_manager.py`: Flask Web 服务，提供 API 和页面支持。
  * `src/templates/`: 前端 HTML 模板。
  * `src/static/style.css`: 全新设计的 CSS 样式表。

## 📄 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 授权。

```
```
