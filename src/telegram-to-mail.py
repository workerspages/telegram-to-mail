import asyncio
import os
import json
import aiohttp
import random
import hashlib
from datetime import datetime, time as dt_time
# 核心依赖：Telethon 及其错误处理
from telethon import TelegramClient, events, errors
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from bs4 import BeautifulSoup

# --- 定义常量 ---
CONFIG_FILE = 'config.json'
SESSION_DIR = './session_data'
SESSION_NAME = os.path.join(SESSION_DIR, 'telegram.session')
STATE_FILE = os.path.join(SESSION_DIR, 'schedule_state.json')
SCRAPER_STATE_FILE = os.path.join(SESSION_DIR, 'scraper_state.json')

# --- [安全增强] 核心防封发送封装 ---

async def safe_send_message(client, entity, message):
    """
    【安全核心】发送消息的增强封装：
    1. 正确处理 FloodWaitError：捕获 Telegram 的强制等待要求，并自动休眠。
    2. 操作频率控制 (Sleep is your friend)：发送成功后强制随机休眠 3-10 秒，模拟人类操作。
    """
    try:
        # 尝试发送消息
        await client.send_message(entity, message)
        
        # 发送成功后的随机冷却时间，规避机器人特征
        post_delay = random.uniform(3.0, 10.0)
        print(f"[Security] 消息成功发送至 {entity}. 随机冷却 {post_delay:.2f}s (模拟人类读取/输入)...")
        await asyncio.sleep(post_delay)
        return True

    except errors.FloodWaitError as e:
        # Telegram 要求等待 e.seconds 秒
        print(f"[FloodWait] 触发 Telegram 频率限制！必须等待 {e.seconds} 秒。脚本将进入休眠，请勿强行重启。")
        await asyncio.sleep(e.seconds)
        # 休眠结束后自动重试
        return await safe_send_message(client, entity, message)
    
    except Exception as e:
        print(f"[Error] 发送消息至 {entity} 失败: {e}")
        return False

# --- 配置加载与管理 ---

def load_config():
    """从 config.json 加载配置"""
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Config file not found at {CONFIG_FILE}")
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading or parsing config file: {e}")
        return None

def load_state():
    """加载定时任务状态"""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    """保存定时任务状态"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving schedule state: {e}")

def load_scraper_state():
    """加载爬虫状态"""
    if not os.path.exists(SCRAPER_STATE_FILE):
        return {}
    try:
        with open(SCRAPER_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_scraper_state(state):
    """保存爬虫状态"""
    try:
        with open(SCRAPER_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving scraper state: {e}")

def update_msmtp_config(email_config):
    """动态更新 msmtp 配置文件"""
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

# --- 推送服务函数 ---

async def send_email(email_config, subject, body, attachment=None, filename=None):
    """发送邮件功能"""
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
    
    if proc.returncode != 0:
        print(f"msmtp error: {stderr.decode()}")
    else:
        print("Email sent successfully.")

async def send_bark(server_url, token, title, content):
    """发送 Bark 推送"""
    base_url = server_url.rstrip('/')
    url = f"{base_url}/{token}/{title}/{content}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Failed to send Bark notification. Status: {response.status}")
            else:
                print(f"Bark notification sent successfully.")

async def send_pushplus(token, title, content):
    """发送 Pushplus 推送"""
    url = "https://www.pushplus.plus/send"
    payload = {"token": token, "title": title, "content": content}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                print(f"Failed to send Pushplus notification. Status: {response.status}")
            else:
                print("Pushplus notification sent successfully.")

# --- 辅助提取配置函数 ---

def get_bark_details(config, bark_id):
    notifiers_config = config.get('notifiers', {})
    if 'bark' in notifiers_config:
        for bark_notifier in notifiers_config['bark']:
            if bark_notifier.get('id') == bark_id:
                return {
                    "token": bark_notifier.get('token'),
                    "server_url": bark_notifier.get('server_url')
                }
    return None

def get_pushplus_token(config, pushplus_id):
    notifiers_config = config.get('notifiers', {})
    if 'pushplus' in notifiers_config:
        for pushplus_notifier in notifiers_config['pushplus']:
            if pushplus_notifier.get('id') == pushplus_id:
                return pushplus_notifier.get('token')
    return None

async def send_delayed_reply(client, chat_id, message, delay=5):
    """
    带随机波动的延迟回复：
    在设定的延迟基础上，额外增加随机的 1-3 秒波动，模拟人类打字速度。
    """
    actual_delay = delay + random.uniform(1.0, 3.0)
    print(f"[Auto-Reply] Planned {delay}s, Jittered to {actual_delay:.2f}s. Waiting...")
    await asyncio.sleep(actual_delay)
    
    # 使用安全发送函数
    await safe_send_message(client, chat_id, message)

# --- 核心消息处理 ---

async def process_notifications(config, notifiers_list, subject, body):
    """分发通知到各个通道"""
    for nid in notifiers_list:
        try:
            if nid.startswith('bark'):
                bark_details = get_bark_details(config, nid)
                if bark_details and bark_details.get('token'):
                    server_url = bark_details.get('server_url') or "https://api.day.app"
                    await send_bark(server_url, bark_details['token'], subject, body)

            elif nid.startswith('pushplus'):
                token = get_pushplus_token(config, nid)
                if token:
                    await send_pushplus(token, subject, body)
                    
            elif nid == "email":
                if 'email' in config.get('notifiers', {}):
                    await send_email(config['notifiers']['email'], subject, body)
        except Exception as e:
            print(f"[ERROR] Failed to process notifier '{nid}': {e}")

async def handle_message(event):
    """Telethon 事件处理"""
    config = load_config()
    if not config:
        return

    chat_id = str(event.chat_id)
    group = next((g for g in config.get('groups', []) if g.get('id') == chat_id), None)
    
    if not group:
        return

    message_text = event.message.text or ""
    sender = await event.message.get_sender()
    sender_info = f"{sender.first_name or ''} {sender.last_name or ''} (@{getattr(sender, 'username', 'N/A')})" if sender else "Unknown Sender"
    
    group_name = group.get('name', 'Unknown Group')
    subject = f"【TG消息】{group_name}"
    body = f"发信人: {sender_info}\n\n{message_text}"

    notifiers_to_trigger = set()
    keyword_matched = False

    for keyword_rule in group.get('keywords', []):
        if keyword_rule.get('word') and keyword_rule.get('word') in message_text:
            notifiers_to_trigger.update(keyword_rule.get('notifiers', []))
            keyword_matched = True
            
            reply_content = keyword_rule.get('reply_content')
            if reply_content:
                try:
                    delay_seconds = float(keyword_rule.get('reply_delay', 5))
                except:
                    delay_seconds = 5
                
                # 异步执行延迟回复
                asyncio.create_task(send_delayed_reply(event.client, event.chat_id, reply_content, delay_seconds))

    if not keyword_matched:
        notifiers_to_trigger.update(group.get('default_notifiers', []))

    if notifiers_to_trigger:
        await process_notifications(config, list(notifiers_to_trigger), subject, body)

# --- 工作线程：网页爬虫 (免登录模式) ---

async def scraper_task_worker():
    """解析公开频道网页预览，零风险获取新消息"""
    print("Web Scraper worker started.")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    while True:
        try:
            config = load_config()
            scraper_state = load_scraper_state()
            
            if config:
                channels = config.get('scrape_channels', [])
                for channel in channels:
                    if not channel.get('enabled', True):
                        continue

                    username = channel.get('username', '').replace('@', '')
                    if not username: continue

                    url = f"https://t.me/s/{username}"
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url, headers=headers, timeout=15) as resp:
                                if resp.status == 200:
                                    html = await resp.text()
                                    soup = BeautifulSoup(html, 'html.parser')
                                    msgs = soup.select('.tgme_widget_message_text')
                                    
                                    if msgs:
                                        latest_msg_html = msgs[-1]
                                        latest_text = latest_msg_html.get_text(separator='\n').strip()
                                        msg_hash = hashlib.md5(latest_text.encode('utf-8')).hexdigest()
                                        
                                        if scraper_state.get(username) != msg_hash:
                                            print(f"[Scraper] New message in @{username}")
                                            scraper_state[username] = msg_hash
                                            save_scraper_state(scraper_state)
                                            
                                            display_name = channel.get('name') or f"@{username}"
                                            subject = f"【TG订阅】{display_name} 更新"
                                            body = f"{latest_text}\n\n(来源: Web Scraper)"
                                            
                                            await process_notifications(config, channel.get('notifiers', []), subject, body)
                    except Exception as e:
                        print(f"[Scraper] Error scraping {username}: {e}")
                    
                    # 避免 IP 抓取过于频繁
                    await asyncio.sleep(random.uniform(2.0, 5.0))
            
            interval = int((config or {}).get('scraper_interval', 60))
            await asyncio.sleep(max(interval, 15))

        except Exception as e:
            print(f"Error in scraper worker: {e}")
            await asyncio.sleep(60)

# --- 工作线程：定时任务 (需登录，安全发送) ---

async def scheduled_task_worker(client):
    """处理带有随机时段触发的定时发送任务"""
    print("Scheduled task worker started.")
    daily_random_targets = {}

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            config = load_config()
            state = load_state()
            
            if config:
                tasks = config.get('scheduled_tasks', [])
                for idx, task in enumerate(tasks):
                    if not task.get('enabled', True):
                        continue

                    target = task.get('target')
                    msg = task.get('message')
                    task_sig = f"{target}_{idx}"
                    
                    # 今日已执行则跳过
                    if state.get(task_sig) == today_str:
                        continue

                    t_start_str = task.get('time_start') or "08:00"
                    t_end_str = task.get('time_end') or "09:00"
                    
                    # 为今天生成一个该任务的随机执行时间戳
                    rand_key = f"{task_sig}_{today_str}"
                    if rand_key not in daily_random_targets:
                        try:
                            h_s, m_s = map(int, t_start_str.split(':'))
                            h_e, m_e = map(int, t_end_str.split(':'))
                            dt_start = now.replace(hour=h_s, minute=m_s, second=0, microsecond=0)
                            dt_end = now.replace(hour=h_e, minute=m_e, second=0, microsecond=0)
                            
                            if dt_end > dt_start:
                                daily_random_targets[rand_key] = random.uniform(dt_start.timestamp(), dt_end.timestamp())
                                exec_time = datetime.fromtimestamp(daily_random_targets[rand_key]).strftime('%H:%M:%S')
                                print(f"[Schedule] Task {idx} scheduled at {exec_time} today.")
                        except:
                            continue
                    
                    # 检查是否到达生成的随机触发点
                    if rand_key in daily_random_targets and now.timestamp() >= daily_random_targets[rand_key]:
                        print(f"[Schedule] Executing task {idx} now...")
                        # 使用安全发送函数
                        success = await safe_send_message(client, target, msg)
                        if success:
                            state[task_sig] = today_str
                            save_state(state)
                            if rand_key in daily_random_targets:
                                del daily_random_targets[rand_key]

            # 每分钟轮询一次检查任务
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Error in scheduled worker: {e}")
            await asyncio.sleep(60)

# --- 主程序入口 ---

async def main():
    print("=== Telegram to Mail & Task Engine Starting ===")
    
    # 1. 启动独立于客户端的网页爬虫
    asyncio.create_task(scraper_task_worker())

    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    # 情况 A: 缺少 API 凭证
    if not api_id or not api_hash:
        print("[Warning] API_ID or API_HASH not set. Telegram Client disabled.")
        while True: await asyncio.sleep(3600)
        return

    # 情况 B: 缺少会话文件 (Docker 中无法进行初始验证码登录)
    if not os.path.exists(SESSION_NAME):
        print("------------------------------------------------------------------")
        print(f"Notice: Session file not found: {SESSION_NAME}")
        print("Telegram Client (Listener/Forwarder/Scheduler) will be skipped.")
        print("Please upload a valid .session file to the data/session_data folder.")
        print("------------------------------------------------------------------")
        while True: await asyncio.sleep(3600)
        return

    # 情况 C: 尝试启动 Telegram 客户端
    try:
        client = TelegramClient(SESSION_NAME, int(api_id), api_hash)
        
        @client.on(events.NewMessage)
        async def event_handler(event):
            await handle_message(event)

        print("[Client] Connecting to Telegram...")
        await client.start()
        print("[Client] Connected successfully. Listener active.")
        
        # 启动依赖客户端的定时随机任务
        client.loop.create_task(scheduled_task_worker(client))
        
        await client.run_until_disconnected()

    except Exception as e:
        print(f"[Client] Fatal error in client mode: {e}")
        # 客户端崩溃后，主进程保持存活以便爬虫继续运行
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    # 确保持久化目录存在
    if not os.path.exists(SESSION_DIR):
        os.makedirs(SESSION_DIR)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit by user.")
