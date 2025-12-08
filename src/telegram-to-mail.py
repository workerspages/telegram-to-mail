import asyncio
import os
import json
import aiohttp
import random
from datetime import datetime, time as dt_time
from telethon import TelegramClient, events
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# 定义常量
CONFIG_FILE = 'config.json'
SESSION_DIR = './session_data'
SESSION_NAME = os.path.join(SESSION_DIR, 'telegram.session')
STATE_FILE = os.path.join(SESSION_DIR, 'schedule_state.json')

# --- 配置加载与管理 ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading config: {e}")
        return None

def load_state():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f: json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e: print(f"Error saving state: {e}")

def update_msmtp_config(email_config):
    conf = f"""defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /dev/stdout

account        default
host           {email_config.get('msmtp_host', '')}
port           {email_config.get('msmtp_port', '587')}
from           {email_config.get('msmtp_from', '')}
user           {email_config.get('msmtp_user', '')}
password       {email_config.get('msmtp_pass', '')}
"""
    try:
        with open('/etc/msmtprc', 'w') as f:
            f.write(conf)
        os.chmod('/etc/msmtprc', 0o600)
    except IOError as e:
        print(f"Error writing msmtp config: {e}")

# --- 推送服务 ---
async def send_email(email_config, subject, body, attachment=None, filename=None):
    update_msmtp_config(email_config)
    msg = MIMEMultipart()
    msg['From'] = email_config.get('msmtp_from')
    msg['To'] = email_config.get('msmtp_from')
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
    stdout, stderr = await proc.communicate(input=raw_bytes)
    if proc.returncode != 0: print(f"msmtp error: {stderr.decode()}")
    else: print("Email sent successfully.")

async def send_bark(server_url, token, title, content):
    base_url = server_url.rstrip('/')
    url = f"{base_url}/{token}/{title}/{content}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Failed to send Bark. Status: {response.status}")
            else:
                print(f"Bark sent via {base_url}.")

async def send_pushplus(token, title, content):
    url = "https://www.pushplus.plus/send"
    payload = {"token": token, "title": title, "content": content}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                print(f"Failed to send Pushplus. Status: {response.status}")
            else:
                print("Pushplus sent.")

# --- 辅助函数 ---
def get_bark_details(config, bark_id):
    notifiers_config = config.get('notifiers', {})
    if 'bark' in notifiers_config:
        for n in notifiers_config['bark']:
            if n.get('id') == bark_id:
                return {"token": n.get('token'), "server_url": n.get('server_url')}
    return None

def get_pushplus_token(config, pushplus_id):
    notifiers_config = config.get('notifiers', {})
    if 'pushplus' in notifiers_config:
        for n in notifiers_config['pushplus']:
            if n.get('id') == pushplus_id:
                return n.get('token')
    return None

# --- ★★★ 核心修改：支持自定义延迟 ★★★ ---
async def send_delayed_reply(client, chat_id, message, delay=5):
    """延迟指定秒数后发送回复消息"""
    if delay > 0:
        await asyncio.sleep(delay)
    try:
        await client.send_message(chat_id, message)
        print(f"[Auto-Reply] Sent reply to {chat_id} after {delay}s: {message}")
    except Exception as e:
        print(f"[Auto-Reply] Failed to send reply: {e}")

async def process_notifications(config, notifiers_list, subject, body):
    for nid in notifiers_list:
        try:
            if nid.startswith('bark'):
                details = get_bark_details(config, nid)
                if details and details.get('token'):
                    url = details.get('server_url') or "https://api.day.app"
                    await send_bark(url, details['token'], subject, body)
            elif nid.startswith('pp'):
                token = get_pushplus_token(config, nid)
                if token: await send_pushplus(token, subject, body)
            elif nid == "email":
                if 'email' in config.get('notifiers', {}):
                    await send_email(config['notifiers']['email'], subject, body)
        except Exception as e:
            print(f"[ERROR] Notifier '{nid}' failed: {e}")

async def handle_message(event):
    config = load_config()
    if not config: return

    chat_id = str(event.chat_id)
    group = next((g for g in config.get('groups', []) if g.get('id') == chat_id), None)
    if not group: return

    message_text = event.message.text or ""
    sender = await event.message.get_sender()
    sender_info = f"{sender.first_name or ''} {sender.last_name or ''} (@{getattr(sender, 'username', 'N/A')})" if sender else "Unknown"
    
    group_name = group.get('name', 'Unknown')
    subject = f"【Telegram】来自 {group_name} 的新消息"
    body = f"发信人: {sender_info}\n\n{message_text}"

    notifiers_to_trigger = set()
    keyword_matched = False
    client = event.client

    for rule in group.get('keywords', []):
        if rule.get('word') and rule.get('word') in message_text:
            notifiers_to_trigger.update(rule.get('notifiers', []))
            keyword_matched = True
            
            # --- 自动回复逻辑 ---
            reply_content = rule.get('reply_content')
            if reply_content:
                # 获取配置的延迟时间，默认5秒
                try:
                    delay = float(rule.get('reply_delay', 5))
                except (ValueError, TypeError):
                    delay = 5
                    
                print(f"Keyword '{rule.get('word')}' matched. Reply in {delay}s.")
                asyncio.create_task(send_delayed_reply(client, event.chat_id, reply_content, delay))

    if not keyword_matched:
        notifiers_to_trigger.update(group.get('default_notifiers', []))

    if notifiers_to_trigger:
        print(f"Triggering notifiers: {list(notifiers_to_trigger)}")
        await process_notifications(config, list(notifiers_to_trigger), subject, body)

async def scheduled_task_worker(client):
    print("Scheduled task worker started.")
    daily_random_targets = {}
    last_check_minute = None

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            current_minute_str = now.strftime("%H:%M")
            
            if last_check_minute == current_minute_str:
                await asyncio.sleep(1)
                continue
                
            config = load_config()
            state = load_state()
            
            if config:
                tasks = config.get('scheduled_tasks', [])
                for idx, task in enumerate(tasks):
                    if not task.get('enabled', True): continue

                    target = task.get('target')
                    msg = task.get('message')
                    task_sig = f"{target}_{msg}_{task.get('time_start')}_{task.get('time_end')}_{idx}"
                    
                    if state.get(task_sig) == today_str: continue

                    t_start = task.get('time_start') or task.get('time') or "08:00"
                    t_end = task.get('time_end') or task.get('time') or "08:00"
                    
                    try:
                        h_s, m_s = map(int, t_start.split(':'))
                        h_e, m_e = map(int, t_end.split(':'))
                        dt_start = now.replace(hour=h_s, minute=m_s, second=0, microsecond=0)
                        dt_end = now.replace(hour=h_e, minute=m_e, second=0, microsecond=0)
                        
                        if dt_end < dt_start or now < dt_start or now > dt_end: continue
                        
                        target_key = f"{task_sig}_{today_str}"
                        if target_key not in daily_random_targets:
                            ts_min = max(now.timestamp(), dt_start.timestamp())
                            ts_max = dt_end.timestamp()
                            if ts_max > ts_min:
                                rand_dt = datetime.fromtimestamp(random.uniform(ts_min, ts_max))
                            else:
                                rand_dt = now
                            daily_random_targets[target_key] = rand_dt
                            print(f"[Schedule] Task {idx} set for {rand_dt.strftime('%H:%M:%S')}")
                        
                        target_dt = daily_random_targets[target_key]
                        
                        if now >= target_dt:
                            entity = int(target) if target.lstrip('-').isdigit() else target
                            await client.send_message(entity, msg)
                            print(f"[Schedule] Sent '{msg}' to {target}")
                            state[task_sig] = today_str
                            save_state(state)
                            if target_key in daily_random_targets: del daily_random_targets[target_key]
                                
                    except Exception as e:
                        print(f"[Schedule] Error task {idx}: {e}")

            last_check_minute = current_minute_str
            await asyncio.sleep(60 - datetime.now().second)
            
        except Exception as e:
            print(f"Worker error: {e}")
            await asyncio.sleep(60)

async def main():
    print("Starting client...")
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    if not api_id or not api_hash: return print("Missing API_ID/HASH")

    client = TelegramClient(SESSION_NAME, int(api_id), api_hash)
    
    @client.on(events.NewMessage)
    async def event_handler(event):
        await handle_message(event)

    try:
        await client.start()
        print("Client started.")
        client.loop.create_task(scheduled_task_worker(client))
        await client.run_until_disconnected()
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        if client.is_connected(): await client.disconnect()

if __name__ == '__main__':
    if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
