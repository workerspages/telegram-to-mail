import asyncio, os, json, aiohttp
from telethon import TelegramClient, events
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

CONFIG_FILE = 'config.json'
SESSION_DIR = './session_data'
SESSION_NAME = os.path.join(SESSION_DIR, 'telegram.session')

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_msmtp(emailcfg):
    conf = f"""defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /dev/stdout

account        default
host           {emailcfg['msmtp_host']}
port           {emailcfg.get('msmtp_port','587')}
from           {emailcfg['msmtp_from']}
user           {emailcfg['msmtp_user']}
password       {emailcfg['msmtp_pass']}
"""
    with open('/etc/msmtprc', 'w') as f:
        f.write(conf)
    os.chmod('/etc/msmtprc', 0o600)

async def send_email(emailcfg, subject, body, attachment=None, filename=None):
    update_msmtp(emailcfg)
    msg = MIMEMultipart()
    msg['From'] = emailcfg['msmtp_from']
    msg['To'] = emailcfg['msmtp_from']
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
        stdin=asyncio.subprocess.PIPE
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
    if method == 'bark':
        for nid in ids:
            for nt in config['notifiers']['bark']:
                if nt['id'] == nid:
                    arr.append(nt['token'])
    if method == 'pushplus':
        for nid in ids:
            for nt in config['notifiers']['pushplus']:
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
    senderinfo = f"{sender.first_name or ''} {sender.last_name or ''} ({getattr(sender, 'username', '')})" if sender else ""
    body = f"From: {senderinfo}\n\n{msg}"

    for kw in group.get('keywords', []):
        if kw['word'] in msg:
            for nid in kw['notifiers']:
                if nid.startswith('bark'):
                    for t in get_notifier_token_list(config, [nid], 'bark'):
                        await send_bark(t, subject, body)
                elif nid.startswith('pp'):
                    for t in get_notifier_token_list(config, [nid], 'pushplus'):
                        await send_pushplus(t, subject, body)
                elif nid == "email":
                    await send_email(config['notifiers']['email'], subject, body)
    for nid in group.get('default_notifiers', []):
        if nid.startswith('bark'):
            for t in get_notifier_token_list(config, [nid], 'bark'):
                await send_bark(t, subject, body)
        elif nid.startswith('pp'):
            for t in get_notifier_token_list(config, [nid], 'pushplus'):
                await send_pushplus(t, subject, body)
        elif nid == "email":
            await send_email(config['notifiers']['email'], subject, body)

async def main():
    config = load_config()
    API_ID = int(os.getenv('API_ID', '12345678'))
    API_HASH = os.getenv('API_HASH', '0123456789abcdef0123456789abcdef')
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        @client.on(events.NewMessage)
        async def _(event):
            await handle_message(event)
        await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
