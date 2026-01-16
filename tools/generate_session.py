"""
Telegram Session 生成工具

功能：
1. 使用手机号登录 Telegram，生成 telegram.session 文件
2. 自动转换为 StringSession 格式
3. 自动生成 Base64 编码（用于环境变量）

使用方法：
  pip install telethon
  python generate_session.py

输出文件：
  - telegram.session  : SQLite 格式（可直接上传到 Docker）
  - session.string    : StringSession 格式（纯文本）
  - SESSION_STRING 环境变量值会打印到控制台
"""

import base64
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("=" * 60)
print("Telegram Session 生成工具")
print("=" * 60)
print()

# 获取 API 凭据
print("请前往 https://my.telegram.org 获取 API_ID 和 API_HASH")
print()
API_ID = input("请输入 API_ID: ").strip()
API_HASH = input("请输入 API_HASH: ").strip()

if not API_ID or not API_HASH:
    print("错误: API_ID 和 API_HASH 不能为空")
    exit(1)

print()
print("正在启动 Telegram 登录...")
print("(将要求输入手机号和验证码)")
print()

# 创建客户端并登录
# 这会在当前目录生成 telegram.session 文件
client = TelegramClient("telegram", int(API_ID), API_HASH)

with client:
    # 获取当前用户信息确认登录成功
    me = client.get_me()
    print()
    print(f"✅ 登录成功！")
    print(f"   用户: {me.first_name} {me.last_name or ''}")
    print(f"   用户名: @{me.username or 'N/A'}")
    print(f"   ID: {me.id}")
    print()
    
    # 获取 StringSession
    string_session = StringSession.save(client.session)
    
    # 保存到 session.string 文件
    with open("session.string", "w") as f:
        f.write(string_session)
    
    # 生成 Base64 编码
    session_b64 = base64.b64encode(string_session.encode('utf-8')).decode('utf-8')

print("=" * 60)
print("生成的文件:")
print("=" * 60)
print()
print("1. telegram.session (SQLite 格式)")
print("   用途: 上传到 Docker 容器的 /app/data/ 或 /app/data/session_data/")
print()
print("2. session.string (StringSession 格式)")
print("   用途: 上传到 Docker 容器的 /app/data/")
print()
print("=" * 60)
print("环境变量 SESSION_STRING (Base64 编码):")
print("=" * 60)
print()
print(session_b64)
print()
print("=" * 60)
print("复制上面的 Base64 字符串，设置为环境变量 SESSION_STRING")
print("适用于不支持文件上传的 PaaS 平台")
print("=" * 60)
