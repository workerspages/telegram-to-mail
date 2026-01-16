"""
将现有的 telegram.session (SQLite) 转换为 Base64 编码的 SESSION_STRING

使用方法:
1. 将 telegram.session 文件放在与此脚本同目录
2. 运行: python convert_session.py
3. 复制输出的 Base64 字符串设置为环境变量 SESSION_STRING
"""

import base64
import os

# 检查 telethon 是否安装
try:
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("错误: 请先安装 telethon")
    print("运行: pip install telethon")
    exit(1)

# 检查 session 文件是否存在
SESSION_FILE = "telegram"  # 不带 .session 后缀

if not os.path.exists(f"{SESSION_FILE}.session"):
    print(f"错误: 未找到 {SESSION_FILE}.session 文件")
    print("请将 telegram.session 文件放在与此脚本同目录下")
    exit(1)

print("=" * 60)
print("Telegram Session 转换工具")
print("=" * 60)
print()

# 获取 API 凭据 (必须与生成 session 时使用的相同)
print("请输入生成此 session 时使用的 API 凭据：")
API_ID = input("API_ID: ").strip()
API_HASH = input("API_HASH: ").strip()

if not API_ID or not API_HASH:
    print("错误: API_ID 和 API_HASH 不能为空")
    exit(1)

print()
print(f"正在读取 {SESSION_FILE}.session ...")

try:
    # 使用现有的 SQLite session 文件创建客户端
    client = TelegramClient(SESSION_FILE, int(API_ID), API_HASH)
    
    with client:
        # 验证 session 有效
        me = client.get_me()
        print(f"✅ Session 有效！")
        print(f"   用户: {me.first_name} {me.last_name or ''} (@{me.username or 'N/A'})")
        print()
        
        # 获取 StringSession 字符串
        string_session = StringSession.save(client.session)
        
        # 保存到 session.string 文件
        with open("session.string", "w") as f:
            f.write(string_session)
        print("已保存: session.string")
        
        # 生成 Base64 编码
        session_b64 = base64.b64encode(string_session.encode('utf-8')).decode('utf-8')

    print()
    print("=" * 60)
    print("SESSION_STRING (Base64 编码):")
    print("=" * 60)
    print()
    print(session_b64)
    print()
    print("=" * 60)
    print("复制上面的字符串，设置为环境变量 SESSION_STRING")
    print("=" * 60)

except Exception as e:
    print(f"错误: {e}")
    exit(1)
