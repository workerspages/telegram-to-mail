
# Telegram to Mail & More - 智能 Telegram 消息转发中心

[![GitHub Actions CI/CD](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/workerspages/telegram-to-mail/actions/workflows/build-and-push.yml)
[![Docker Image](https://img.shields.io/docker/pulls/workerspages/telegram-to-mail.svg)](https://hub.docker.com/r/workerspages/telegram-to-mail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](README.en.md)** | **[简体中文](README.md)**

一个功能强大、易于部署的 Telegram 消息转发工具。它可以实时监听指定的 Telegram 群组消息，并根据您设定的关键字规则，通过多种渠道（Email, Bark, Pushplus）将重要信息推送给您，有效过滤噪音，聚焦核心资讯。

项目内置了一个现代化、响应式的 Web UI 管理面板，让所有配置操作都变得简单直观。

![Web UI 界面截图](https://user-images.githubusercontent.com/your-image-url.png) <!-- 建议您将最终的界面截图上传到 issue 中，然后替换这里的链接 -->

---

## ✨ 核心功能

*   **实时群组监听**: 基于 Telethon 库，稳定、高效地接收指定 Telegram 群组的新消息。
*   **多通道消息推送**:
    *   **Email**: 通过配置 SMTP 服务器将消息作为邮件发送。
    *   **Bark**: 为苹果生态用户提供即时推送通知。
    *   **Pushplus**: 兼容性广泛的微信消息推送服务。
*   **精细化关键字过滤**: 可为每个群组设置多个关键字规则，不同的关键字可触发不同的推送通道，实现精准推送。
*   **现代化 Web UI**:
    *   安全的用户登录认证。
    *   直观的卡片式、可折叠界面，用于管理多个群组配置。
    *   在网页上即可轻松完成所有推送通道和群组规则的增删改查。
    *   所有修改**即时保存**，无需额外的“保存”按钮。
*   **可选的 Cloudflare Tunnel**:
    *   **零端口暴露**: 无需在您的服务器上开放任何端口，即可通过 Cloudflare 的安全隧道将 Web UI 暴露到公网。
    *   **环境变量启用**: 只需一个环境变量即可启用此功能，对不使用的用户完全无影响。
*   **容器化与自初始化**:
    *   通过 Docker 和 Docker Compose 一键部署。
    *   容器**自我初始化**，无需在部署前手动创建任何配置文件，兼容各类自动化部署平台。

---

## 🚀 快速部署指南

部署本项目非常简单，您只需要准备好以下环境即可。

### 先决条件

1.  一台已安装 [Docker](https://www.docker.com/) 和 [Docker Compose](https://docs.docker.com/compose/install/) 的服务器。
2.  一个 Telegram 账号，并已从 [my.telegram.org](https://my.telegram.org) 获取到 `API_ID` 和 `API_HASH`。

### 部署步骤

**第一步：克隆本项目**
```bash
git clone https://github.com/workerspages/telegram-to-mail.git
cd telegram-to-mail
```

**第二步：配置 `docker-compose.yml`**

打开项目根目录下的 `docker-compose.yml` 文件，您需要根据注释填写 `environment` 部分的变量。

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
> **安全提示**: `WEB_SECRET_KEY` 关系到您登录状态的安全，请务必使用一个复杂的、无规律的随机字符串。

**第三步：构建并启动服务**

在项目根目录下执行以下命令：
```bash
docker-compose build
docker-compose up -d
```
容器将在后台启动。`entrypoint.sh` 脚本会自动处理所有初始化工作。

**第四步：首次登录与 Telegram 授权**

1.  **访问 Web UI**: 打开浏览器，访问 `http://<您的服务器IP>:5000`。
2.  **首次授权**: 第一次启动时，程序需要登录您的 Telegram 账号。请查看容器日志以完成授权。
    ```bash
    docker-compose logs -f
    ```
    日志中会提示您输入电话号码、密码（如果设置了二次验证），或扫描二维码。请按照提示在终端中完成操作。成功登录后，会在 `./data/session_data` 目录下生成一个 session 文件，后续启动将无需再次授权。

---

## 🔧 使用配置指南

成功登录后，您就可以在 Web UI 中进行所有配置了。

### 1. 配置推送通道

![推送通道设置](https://user-images.githubusercontent.com/your-image-url2.png) <!-- 建议您将最终的界面截图上传到 issue 中，然后替换这里的链接 -->

*   点击页面右上角的**齿轮图标**⚙️，打开“推送通道设置”弹窗。
*   **Email (SMTP)**: 填写您的 SMTP 服务器信息。
*   **Bark/Pushplus**: 点击“添加 Token”按钮，可以创建多个不同的推送目标。`ID` 会自动生成，您只需填写 `Token` 即可。
*   所有修改在点击“保存通道设置”后会**立即生效**。

### 2. 添加和管理群组

![群组管理](https://user-images.githubusercontent.com/your-image-url3.png) <!-- 建议您将最终的界面截图上传到 issue 中，然后替换这里的链接 -->

*   点击右上角的“**+ 添加群组**”按钮。
*   **群组ID**: 填入您要监听的群组的数字 ID。通常是一个以 `-100` 开头的长数字。
    > *如何获取群组ID？* 将您的机器人（如 `@userinfobot`）添加到群组中，它会返回群组的 ID。
*   **群组名称**: 只是一个方便您辨认的备注。
*   **默认推送通道**: 在这里选择的通道，会接收该群组的**所有**消息。
*   **关键字推送**:
    *   点击“添加关键字”可以创建一条新规则。
    *   在输入框中填写您关心的词语。
    *   在下方的复选框中选择这个关键字应该推送到哪些通道。
*   所有修改（包括添加、删除、勾选/取消勾选）都会**自动、立即保存**到服务器，无需额外操作。
*   点击卡片头部可以在**展开/折叠**之间切换，方便管理。

---

## 🌐 进阶功能：使用 Cloudflare Tunnel

如果您希望安全地从公网访问管理面板，而不想暴露服务器的任何端口，可以使用此功能。

1.  **获取 Token**: 登录您的 [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)，创建一个新的 Tunnel，并复制生成的 Token 字符串。
2.  **配置 Token**: 打开 `docker-compose.yml` 文件，将您的 Token 填入 `TUNNEL_TOKEN` 环境变量。
    ```yaml
    environment:
      # ... 其他变量 ...
      - TUNNEL_TOKEN=ey...your...very...long...token...Q=
    ```
3.  **(推荐) 禁用端口映射**: 为了达到最高的安全性，您可以注释掉 `ports` 部分。
    ```yaml
    # ports:
    #  - "5000:5000"
    ```
4.  **重建并重启服务**:
    ```bash
    docker-compose build
    docker-compose up -d
    ```
    启动后，服务将通过您在 Cloudflare 上设置的域名进行访问。

## 🛠️ 致开发者

本项目结构清晰，易于二次开发。

*   **后端**: 位于 `src/` 目录，`telegram-to-mail.py` 负责消息监听与转发，`web_manager.py` 提供了 Flask Web 服务。
*   **前端**: 位于 `src/templates/` 和 `src/static/`，使用原生 HTML/CSS/JS，无复杂框架。
*   **容器化**: `Dockerfile`, `entrypoint.sh` 和 `docker-compose.yml` 定义了容器的构建与运行方式。

欢迎通过 Pull Request 贡献代码，或在 Issues 中提出宝贵的建议。

## 📄 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 授权。
