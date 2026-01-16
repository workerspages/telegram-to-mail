# Telegram Session 生成工具

一站式工具，用于生成 Telegram 登录会话凭证。

## 前置准备

1. **获取 API 凭据**
   - 访问 [https://my.telegram.org](https://my.telegram.org)
   - 登录后进入 "API development tools"
   - 创建应用，获取 `API_ID` 和 `API_HASH`

2. **安装依赖**
   ```bash
   pip install telethon
   ```

## 使用方法

```bash
python generate_session.py
```

按提示输入：
1. API_ID
2. API_HASH
3. 手机号（带国际区号，如 +8613812345678）
4. 验证码（Telegram 会发送到你的账号）

## 输出文件

运行后会在当前目录生成以下文件：

| 文件名 | 格式 | 说明 |
|--------|------|------|
| `telegram.session` | SQLite 数据库 | Telethon 默认格式 |
| `session.string` | 纯文本 | StringSession 格式 |

同时控制台会输出 **Base64 编码的 SESSION_STRING**，用于环境变量。

## 部署方式

根据你的部署平台，选择以下任一方式：

### 方式 1：上传 SQLite 文件（推荐）

将 `telegram.session` 上传到 Docker 容器：

```
/app/data/telegram.session
# 或
/app/data/session_data/telegram.session
```

### 方式 2：上传 StringSession 文件

将 `session.string` 上传到 Docker 容器：

```
/app/data/session.string
```

### 方式 3：使用环境变量（适用于 PaaS）

适用于不支持文件上传的平台（如 Railway、Render 等）。

1. 复制控制台输出的 Base64 字符串
2. 设置环境变量：
   ```
   SESSION_STRING=MUJRQU5PVEUuMTA4Li4uLi4u（你的 Base64 字符串）
   ```

**手动生成 Base64（如果需要）：**

```bash
# Linux/Mac
base64 -w 0 session.string

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("session.string"))
```

## Session 加载优先级

应用启动时按以下顺序检查 Session：

1. ✅ 环境变量 `SESSION_STRING`（Base64 编码）
2. ✅ 文件 `telegram.session`（SQLite 格式）
3. ✅ 文件 `session.string`（StringSession 格式）
4. ❌ 无 Session，需要新登录

## 注意事项

> ⚠️ **安全警告**
> 
> Session 文件包含你的 Telegram 登录凭证，请妥善保管：
> - 不要将 session 文件提交到公开仓库
> - 不要分享给他人
> - 如果泄露，请立即在 Telegram 设置中终止该会话

## 常见问题

**Q: 提示 "FloodWaitError"？**  
A: 请求过于频繁，等待提示的秒数后重试。

**Q: 提示 "SessionPasswordNeededError"？**  
A: 你的账号开启了两步验证，需要输入密码。

**Q: Session 失效了怎么办？**  
A: 重新运行此工具生成新的 Session。
