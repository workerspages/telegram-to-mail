import asyncio
import os
import json
import aiohttp
import random
import hashlib
from datetime import datetime, time as dt_time
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError  # ★ 已保留：用于处理频率限制错误
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from bs4 import BeautifulSoup

# 定义常量
CONFIG_FILE = 'config.json'
SESSION_DIR = './session_data'
SESSION_NAME = os.path.join(SESSION_DIR, 'telegram.session')
STATE_FILE = os.path.join(SESSION_DIR, 'schedule_state.json')
SCRAPER_STATE_FILE = os.path.join(SESSION_DIR, 'scraper_state.json')

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

# --- 推送服务 ---
async def send_email(email_config, subject, body, attachment=None, filename=None):
    """发送邮件"""
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
                print(f"Failed to send Bark notification to {base_url}. Status: {response.status}, Response: {await response.text()}")
            else:
                print(f"Bark notification sent successfully via {base_url}.")

async def send_pushplus(token, title, content):
    """发送 Pushplus 推送"""
    url = "https://www.pushplus.plus/send"
    payload = {"token": token, "title": title, "content": content}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                print(f"Failed to send Pushplus notification. Status: {response.status}, Response: {await response.text()}")
            else:
                print("Pushplus notification sent successfully.")

# --- ★ 已保留安全发送核心逻辑 (控制频率 & 错误处理) ★ ---
async def safe_send_message(client, chat_id, message, action_desc="Message"):
    """
    包装 client.send_message，加入随机延时和错误重试逻辑。
    - 模拟人类打字和阅读速度 (Sleep 3-10s)。
    - 捕获 FloodWaitError 并强制休眠。
    """
    # 1. 模拟人类行为：发送前随机休眠 3 到 10 秒
    random_delay = random.uniform(3, 10)
    print(f"[Safety] {action_desc}: Sleeping for {random_delay:.2f}s to mimic human behavior...")
    await asyncio.sleep(random_delay)

    while True:
        try:
            await client.send_message(chat_id, message)
            print(f"[Safety] {action_desc} sent successfully to {chat_id}.")
            break  # 发送成功，跳出循环
        except FloodWaitError as e:
            # 2. 捕获 FloodWaitError：根据 Telegram 要求的时间休眠
            print(f"[Safety] WARNING: Telegram is throttling us! Must wait for {e.seconds} seconds.")
            print(f"[Safety] Sleeping for {e.seconds}s now... DO NOT restart the script.")
            await asyncio.sleep(e.seconds)
            print(f"[Safety] Wait over. Retrying to send {action_desc}...")
        except Exception as e:
            # 捕获其他非频率限制错误
            print(f"[Safety] Unexpected error sending {action_desc} to {chat_id}: {e}")
            break

# --- ★ 新增：异步延迟删除消息逻辑 ★ ---
async def auto_delete_task(client, chat_id, message_id, delay_seconds):
    """
    在指定延迟时间后删除特定的消息。
    """
    if delay_seconds <= 0:
        return
    print(f"[Auto-Delete] Message {message_id} in {chat_id} will be deleted in {delay_seconds} seconds.")
    await asyncio.sleep(delay_seconds)
    try:
        await client.delete_messages(chat_id, [message_id])
        print(f"[Auto-Delete] Message {message_id} in {chat_id} deleted successfully.")
    except Exception as e:
        print(f"[Auto-Delete] Failed to delete message {message_id} in {chat_id}: {e}")

# --- 辅助函数 ---
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
    """延迟发送回复"""
    if delay > 0:
        await asyncio.sleep(delay)
    
    # ★ 修改点：改为使用安全发送函数 ★
    await safe_send_message(client, chat_id, message, action_desc=f"Auto-Reply (init-delay {delay}s)")

# --- 核心消息处理逻辑 ---
async def process_notifications(config, notifiers_list, subject, body):
    """处理并发送一组通知"""
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
            print(f"[ERROR] Failed to process notifier '{nid}'. Reason: {e}")

async def handle_message(event):
    """处理 TG 客户端接收到的新消息"""
    config = load_config()
    if not config:
        return

    chat_id = str(event.chat_id)
    group = next((g for g in config.get('groups', []) if g.get('id') == chat_id), None)
    
    if not group:
        return

    message_text = event.message.text or ""
    message_id = event.message.id
    sender = await event.message.get_sender()
    sender_info = f"{sender.first_name or ''} {sender.last_name or ''} (@{getattr(sender, 'username', 'N/A')})" if sender else "Unknown Sender"
    
    group_name = group.get('name', 'Unknown Group')
    subject = f"【TG消息】{group_name}"
    body = f"发信人: {sender_info}\n\n{message_text}"

    notifiers_to_trigger = set()
    keyword_matched = False

    client = event.client

    # --- A. 原始关键字监听与回复逻辑 (不变) ---
    for keyword_rule in group.get('keywords', []):
        if keyword_rule.get('word') and keyword_rule.get('word') in message_text:
            notifiers_to_trigger.update(keyword_rule.get('notifiers', []))
            keyword_matched = True
            
            reply_content = keyword_rule.get('reply_content')
            if reply_content:
                try:
                    delay_seconds = float(keyword_rule.get('reply_delay', 5))
                except (ValueError, TypeError):
                    delay_seconds = 5
                
                print(f"Keyword matched '{keyword_rule.get('word')}'. Scheduling reply in {delay_seconds}s...")
                asyncio.create_task(send_delayed_reply(client, event.chat_id, reply_content, delay_seconds))

    if not keyword_matched:
        notifiers_to_trigger.update(group.get('default_notifiers', []))

    if notifiers_to_trigger:
        print(f"Message from '{group_name}' triggered notifiers: {list(notifiers_to_trigger)}")
        await process_notifications(config, list(notifiers_to_trigger), subject, body)

    # --- B. ★ 新增：转发消息到其他群组/频道 ★ ---
    forward_configs = group.get('forward_targets', [])
    for fwd in forward_configs:
        target_chat = fwd.get('target_id')
        if target_chat:
            try:
                # 使用安全发送的思路进行转发，避免频率过快
                async def do_forward():
                    await asyncio.sleep(random.uniform(2, 5)) # 模拟人类操作小延时
                    # 如果 target_chat 是数字字符串，转为 int
                    dest = int(target_chat) if target_chat.lstrip('-').isdigit() else target_chat
                    await client.forward_messages(dest, event.message)
                    print(f"[Forward] Message from {group_name} forwarded to {target_chat}")
                
                asyncio.create_task(do_forward())
            except Exception as e:
                print(f"[Forward Error] Failed to forward to {target_chat}: {e}")

    # --- C. ★ 新增：延迟删除该条消息 ★ ---
    if group.get('auto_delete_enabled', False):
        try:
            delete_delay = int(group.get('delete_delay', 60))
            asyncio.create_task(auto_delete_task(client, event.chat_id, message_id, delete_delay))
        except (ValueError, TypeError):
            pass


# --- 网页爬虫工作线程 (无登录模式 - 已保留原逻辑) ---
async def scraper_task_worker():
    """
    独立线程：每隔一段时间去访问 t.me/s/xxx 页面，解析最新消息。
    不需要登录账号。
    """
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
                            async with session.get(url, headers=headers, timeout=10) as resp:
                                if resp.status == 200:
                                    html = await resp.text()
                                    soup = BeautifulSoup(html, 'html.parser')
                                    
                                    # 提取所有消息文本div
                                    msgs = soup.select('.tgme_widget_message_text')
                                    
                                    if msgs:
                                        # 获取最新一条消息
                                        latest_msg_html = msgs[-1]
                                        # 提取纯文本
                                        latest_text = latest_msg_html.get_text(separator='\n').strip()
                                        
                                        # 简单的去重机制：计算 hash
                                        msg_hash = hashlib.md5(latest_text.encode('utf-8')).hexdigest()
                                        last_hash = scraper_state.get(username)
                                        
                                        if msg_hash != last_hash:
                                            # 发现新消息！
                                            print(f"[Scraper] New message found in @{username}")
                                            
                                            # 更新状态
                                            scraper_state[username] = msg_hash
                                            save_scraper_state(scraper_state)
                                            
                                            # 触发通知
                                            notifiers = channel.get('notifiers', [])
                                            
                                            # 使用自定义名称或默认用户名
                                            display_name = channel.get('name')
                                            if not display_name:
                                                display_name = f"@{username}"
                                                
                                            subject = f"【TG订阅】{display_name} 更新"
                                            body = f"{latest_text}\n\n(来源: Web Preview)"
                                            
                                            await process_notifications(config, notifiers, subject, body)
                                    else:
                                        # 页面解析不到消息（可能是空频道或结构变了）
                                        pass
                                else:
                                    print(f"[Scraper] Failed to fetch {url}, status: {resp.status}")

                    except Exception as e:
                        print(f"[Scraper] Error scraping {username}: {e}")
                    
                    # 每个频道之间随机休息几秒
                    await asyncio.sleep(random.uniform(2, 5))
            
            # 动态读取轮询频率
            interval = 60
            if config:
                try:
                    interval = int(config.get('scraper_interval', 60))
                    if interval < 10:
                        interval = 10
                except (ValueError, TypeError):
                    interval = 60
            
            await asyncio.sleep(interval)

        except Exception as e:
            print(f"Error in scraper worker: {e}")
            await asyncio.sleep(60)

# --- 定时任务处理逻辑 (依赖客户端 - 已保留原逻辑) ---
async def scheduled_task_worker(client):
    """
    后台任务：每分钟检查定时任务。
    """
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
                    if not task.get('enabled', True):
                        continue

                    target = task.get('target')
                    msg = task.get('message')
                    task_sig = f"{target}_{msg}_{task.get('time_start')}_{task.get('time_end')}_{idx}"
                    
                    if state.get(task_sig) == today_str:
                        continue

                    t_start_str = task.get('time_start') or task.get('time') or "08:00"
                    t_end_str = task.get('time_end') or task.get('time') or "08:00"
                    
                    try:
                        h_s, m_s = map(int, t_start_str.split(':'))
                        h_e, m_e = map(int, t_end_str.split(':'))
                        dt_start = now.replace(hour=h_s, minute=m_s, second=0, microsecond=0)
                        dt_end = now.replace(hour=h_e, minute=m_e, second=0, microsecond=0)
                        
                        if dt_end < dt_start: continue
                        if now < dt_start: continue
                        if now > dt_end: continue
                        
                        target_key = f"{task_sig}_{today_str}"
                        if target_key not in daily_random_targets:
                            time_min_ts = max(now.timestamp(), dt_start.timestamp())
                            time_max_ts = dt_end.timestamp()
                            
                            if time_max_ts > time_min_ts:
                                random_ts = random.uniform(time_min_ts, time_max_ts)
                                random_dt = datetime.fromtimestamp(random_ts)
                            else:
                                random_dt = now
                            
                            daily_random_targets[target_key] = random_dt
                            print(f"[Schedule] Task {idx} target set to {random_dt.strftime('%H:%M:%S')}")
                        
                        target_dt = daily_random_targets[target_key]
                        
                        if now >= target_dt:
                            try:
                                # ★ 修改点：改为使用安全发送函数 ★
                                entity = int(target) if target.lstrip('-').isdigit() else target
                                await safe_send_message(client, entity, msg, action_desc=f"Scheduled Task {idx}")
                                
                                print(f"[Schedule] Executed task {idx}: Sent '{msg}' to {target}")
                                state[task_sig] = today_str
                                save_state(state)
                                if target_key in daily_random_targets:
                                    del daily_random_targets[target_key]
                            except Exception as e:
                                print(f"[Schedule] Failed to send to {target}: {e}")
                                
                    except ValueError:
                        pass

            last_check_minute = current_minute_str
            seconds_to_sleep = 60 - datetime.now().second
            await asyncio.sleep(seconds_to_sleep)
            
        except Exception as e:
            print(f"Error in scheduled worker: {e}")
            await asyncio.sleep(60)

# --- 主程序入口 (已保留原逻辑) ---
async def main():
    """主函数"""
    print("Starting services...")
    
    # 1. 始终启动网页爬虫任务 (独立于 TG 客户端)
    asyncio.create_task(scraper_task_worker())

    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    # 检查是否存在 Session 文件
    session_exists = os.path.exists(SESSION_NAME)

    # 情况 A: 环境变量缺失
    if not api_id or not api_hash:
        print("Warning: API_ID/HASH not set. Telegram Client mode disabled. Only Web Scraper will work.")
        while True:
            await asyncio.sleep(3600)
        return

    # 情况 B: 有 API 配置，但没有 Session 文件 (无法交互登录)
    if not session_exists:
        print("----------------------------------------------------------------")
        print(f"Notice: Session file not found at {SESSION_NAME}")
        print("Interactive login is not supported in this environment.")
        print(">> The Telegram Client (Listen/Forward/Schedule) will be SKIPPED.")
        print(">> The Web Scraper (Anonymous Subscription) is RUNNING.")
        print("----------------------------------------------------------------")
        while True:
            await asyncio.sleep(3600)
        return

    # 情况 C: 有 Session 文件，正常启动客户端
    try:
        api_id = int(api_id)
        client = TelegramClient(SESSION_NAME, api_id, api_hash)
        
        @client.on(events.NewMessage)
        async def event_handler(event):
            await handle_message(event)

        print("Attempting to connect Telegram client...")
        await client.start()
        print("Telegram client started successfully.")
        
        # 启动定时任务 (依赖 Client)
        client.loop.create_task(scheduled_task_worker(client))
        
        await client.run_until_disconnected()

    except Exception as e:
        print(f"Telegram client error: {e}")
        print("Client crashed or failed to start. Keeping process alive for Web Scraper...")
        # 如果客户端崩溃，保持主进程存活以运行爬虫
        while True:
            await asyncio.sleep(60)

if __name__ == '__main__':
    # 确保持久化目录存在
    if not os.path.exists(SESSION_DIR):
        os.makedirs(SESSION_DIR)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user. Exiting.")
