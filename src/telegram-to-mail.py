import asyncio
import os
import sys
import json
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from telethon import TelegramClient, events
import aiohttp

# 发送邮件的函数 (保持和旧版完全兼容)
async def send_email(subject, body_text, attachment=None, filename=None):
    mime_msg = MIMEMultipart()
    mime_msg['From'] = TO_EMAIL
    mime_msg['To'] = TO_EMAIL
    mime_msg['Subject'] = subject
    mime_msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

    if attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        mime_msg.attach(part)

    raw_bytes = mime_msg.as_bytes()
    proc = await asyncio.create_subprocess_exec(
        'msmtp', '-t',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate(input=raw_bytes)

    if proc.returncode == 0:
        print(f"成功转发邮件 (标题: {subject}) 到 {TO_EMAIL}")
    else:
        print(f"邮件转发失败: {stderr.decode()}")

# Bark 推送函数
async def send_bark(token, title, content):
    url = f"https://api.day.app/{token}/{title}/{content}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()

# Pushplus 推送函数
async def send_pushplus(token, title, content):
    url = "http://www.pushplus.plus/send"
    payload = {
        "token": token,
        "title": title,
        "content": content
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()

# 从环境变量安全获取配置
def get_env_var(var_name, is_int=False):
    value = os.getenv(var_name)
    if value is None:
        print(f"错误：环境变量 {var_name} 未设置。")
        sys.exit(1)
    if is_int:
        return int(value)
    return value

API_ID = get_env_var('API_ID', is_int=True)
API_HASH = get_env_var('API_HASH')
SESSION_NAME = get_env_var('SESSION_NAME')
TO_EMAIL = get_env_var('TO_EMAIL')

# Web 配置接口地址，即本机5000端口的接口
WEB_CONFIG_URL = "http://127.0.0.1:5000/api/config"

# 远程获取群组及推送配置
async def fetch_config():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(WEB_CONFIG_URL) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"获取配置失败，HTTP状态码：{resp.status}")
                    return {}
        except Exception as e:
            print(f"请求配置接口异常：{e}")
            return {}

# 监听客户端
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage)
async def message_handler(event):
    msg = event.message
    chat_id = event.chat_id or ''

    print(f"收到群组/频道消息，chat_id={chat_id}，消息ID={msg.id}")

    config = await fetch_config()
    groups_cfg = config.get('groups', {})

    # 查找对应群组配置
    group_cfg = groups_cfg.get(str(chat_id), None)
    if not group_cfg:
        print(f"群组 {chat_id} 未配置，跳过处理")
        return
    
    # 读取推送设置和关键字
    bark_tokens = group_cfg.get('bark_tokens', [])
    pushplus_tokens = group_cfg.get('pushplus_tokens', [])
    keywords_map = group_cfg.get('keywords', {})

    # 构建消息内容
    sender_info = "未知来源"
    try:
        sender = await msg.get_sender()
        if sender:
            sender_info = f"{sender.first_name or ''} {sender.last_name or ''} (@{sender.username or ''})"
        elif msg.chat:
            sender_info = f"{msg.chat.title}"
    except Exception:
        pass

    body_text = f"From: {sender_info}\n\n{msg.text or '[无文本内容]'}"
    subject = "【Telegram】新消息"

    # 判断消息类型及附件
    attachment_data = None
    attachment_filename = None
    if msg.photo:
        subject = "【Telegram】新图片信息"
        attachment_data = await msg.download_media(file=bytes)
        attachment_filename = f"image_{msg.id}.jpg"
    elif msg.document:
        subject = "【Telegram】新附件信息"
        attachment_data = await msg.download_media(file=bytes)
        attachment_filename = msg.document.attributes[-1].file_name or f"file_{msg.id}"
    elif msg.video:
        subject = "【Telegram】新视频信息"
        attachment_data = await msg.download_media(file=bytes)
        attachment_filename = msg.video.attributes[-1].file_name or f"video_{msg.id}.mp4"
    elif msg.text:
        subject = "【Telegram】新文字信息"

    # 先发邮件
    await send_email(subject, body_text, attachment_data, attachment_filename)

    # 根据关键字匹配决定推送通道
    push_tasks = []
    for kw, app in keywords_map.items():
        if kw in (msg.text or ''):
            # 准备调用对应推送api
            if app == 'bark':
                for token in bark_tokens:
                    push_tasks.append(send_bark(token, subject, body_text))
            elif app == 'pushplus':
                for token in pushplus_tokens:
                    push_tasks.append(send_pushplus(token, subject, body_text))
    
    if push_tasks:
        results = await asyncio.gather(*push_tasks, return_exceptions=True)
        for r in results:
            print(f"推送结果: {r}")

async def main():
    print("Userbot 监听服务已启动...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
