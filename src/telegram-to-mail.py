import asyncio, os, sys, json, aiohttp
from telethon import TelegramClient, events
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

CONFIG_FILE = 'config.json'
SESSION_NAME = 'telegram-session'
client = None

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

async def send_email(cfg, subject, body, attachment=None, filename=None):
    msg = MIMEMultipart()
    msg['From'] = cfg['from']
    msg['To'] = cfg['from']
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    if attachment: 
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(part)
    raw_bytes = msg.as_bytes()
    proc = await asyncio.create_subprocess_exec(
        'msmtp', '-t',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate(input=raw_bytes)

async def send_bark(token, title, content):
    url = f"https://api.day.app/{token}/{title}/{content}"
    async with aiohttp.ClientSession() as session:
        await session.get(url)

async def send_pushplus(token, title, content):
    url = "http://www.pushplus.plus/send"
    payload = {"token": token, "title": title, "content": content}
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload)

def get_notifier_token_list(config, ids, method):
    arr = []
    for nid in ids:
        for nt in config['notifiers'][method]:
            if nt['id'] == nid:
                arr.append(nt['token'])
    return arr

async def handle_message(event):
    config = load_config()
    group_id = str(event.chat_id)
    group = next((g for g in config['groups'] if g['id']==group_id), None)
    if not group: return
    msg = event.message.text or ""
    subject = "【Telegram】新消息"
    sender = await event.message.get_sender()
    senderinfo = f"{sender.first_name or ''} {sender.last_name or ''} ({sender.username or ''})" if sender else ""
    body = f"From: {senderinfo}\n\n{msg}"

    # 优先keyword
    for kw in group.get('keywords', []):
        if kw['word'] in msg:
            for nid in kw['notifiers']:
                if nid.startswith('bark'):
                    for t in get_notifier_token_list(config, [nid], 'bark'):
                        await send_bark(t, subject, body)
                elif nid.startswith('pp'):
                    for t in get_notifier_token_list(config, [nid], 'pushplus'):
                        await send_pushplus(t, subject, body)
    # 默认推送
    for nid in group.get('default_notifiers', []):
        if nid.startswith('bark'):
            for t in get_notifier_token_list(config, [nid], 'bark'):
                await send_bark(t, subject, body)
        elif nid.startswith('pp'):
            for t in get_notifier_token_list(config, [nid], 'pushplus'):
                await send_pushplus(t, subject, body)
        elif nid == "email":
            await send_email(config['notifiers']['email'], subject, body)
    await send_email(config['notifiers']['email'], subject, body)

async def main():
    config = load_config()
    API_ID = int(os.getenv('API_ID', '12345678'))
    API_HASH = os.getenv('API_HASH', '0123456789abcdef0123456789abcdef')
    global client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    @client.on(events.NewMessage)
    async def _(event):
        await handle_message(event)
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
