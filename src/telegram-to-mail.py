import asyncio
import os
import json
import aiohttp
import random
import hashlib
import re
from datetime import datetime, time as dt_time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from bs4 import BeautifulSoup
import storage  # 引入 storage 模块

# 初始化存储层
storage.init_storage()

# --- 配置加载与管理 (代理给 storage) ---
def load_config():
    """从存储加载配置"""
    return storage.load_data('config')

def load_state():
    """加载定时任务状态"""
    return storage.load_data('schedule_state', {})

def save_state(state):
    """保存定时任务状态"""
    storage.save_data('schedule_state', state)

def load_scraper_state():
    """加载爬虫状态"""
    return storage.load_data('scraper_state', {})

def save_scraper_state(state):
    """保存爬虫状态"""
    storage.save_data('scraper_state', state)

def update_msmtp_config(email_config):
    """动态更新 msmtp 配置文件 (仅在容器内文件系统有效，PaaS通常是临时文件，重启需重写)"""
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

# --- 安全发送核心逻辑 ---
async def safe_send_message(client, chat_id, message, reply_to=None, action_desc="Message"):
    """
    包装 client.send_message，加入随机延时和错误重试逻辑。
    支持 reply_to 参数。
    """
    random_delay = random.uniform(3, 10)
    print(f"[Safety] {action_desc}: Sleeping for {random_delay:.2f}s to mimic human behavior...")
    await asyncio.sleep(random_delay)

    while True:
        try:
            await client.send_message(chat_id, message, reply_to=reply_to)
            print(f"[Safety] {action_desc} sent successfully to {chat_id}.")
            break
        except FloodWaitError as e:
            print(f"[Safety] WARNING: Telegram is throttling us! Must wait for {e.seconds} seconds.")
            print(f"[Safety] Sleeping for {e.seconds}s now... DO NOT restart the script.")
            await asyncio.sleep(e.seconds)
            print(f"[Safety] Wait over. Retrying to send {action_desc}...")
        except Exception as e:
            print(f"[Safety] Unexpected error sending {action_desc} to {chat_id}: {e}")
            break

# --- Bot API 辅助函数 ---
async def bot_api_request(token, method, data):
    """通用 Bot API 请求函数"""
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                result = await response.json()
                if not result.get('ok'):
                    print(f"[Bot API Error] Method: {method}, Error: {result.get('description')}")
                return result
    except Exception as e:
        print(f"[Bot API Exception] {method}: {e}")
        return None

async def execute_auto_delete(token, chat_id, message_id, delay):
    """执行自动删除任务"""
    if delay > 0:
        await asyncio.sleep(delay)
    
    print(f"[Auto-Delete] Deleting message {message_id} in {chat_id} via Bot...")
    await bot_api_request(token, 'deleteMessage', {
        'chat_id': chat_id,
        'message_id': message_id
    })

async def execute_forward(token, from_chat_id, to_chat_id, message_id):
    """执行消息转发任务 (使用 copyMessage)"""
    print(f"[Forward] Copying message {message_id} from {from_chat_id} to {to_chat_id} via Bot...")
    await bot_api_request(token, 'copyMessage', {
        'chat_id': to_chat_id,
        'from_chat_id': from_chat_id,
        'message_id': message_id
    })

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

async def send_delayed_reply(client, chat_id, message, reply_to=None, delay=5):
    """延迟发送回复"""
    if delay > 0:
        await asyncio.sleep(delay)
    await safe_send_message(client, chat_id, message, reply_to=reply_to, action_desc=f"Auto-Reply (init-delay {delay}s)")

# --- 抽奖自动参与功能 ---
def extract_lottery_keyword(message_text):
    """
    从抽奖消息中提取参与关键词。
    匹配格式: "关键词: 数字/数字=百分比" 例如 "支持老王！VPS8送100台小鸡第五波: 3/36=8.33%"
    返回第一个匹配的关键词，如果没有匹配则返回 None。
    """
    # 匹配 "关键词: 数字/数字=百分比" 格式
    pattern = r'^([^:\n]+?):\s*\d+/\d+=\d+\.?\d*%'
    matches = re.findall(pattern, message_text, re.MULTILINE)
    
    if matches:
        # 返回第一个不是明显系统字段的关键词
        system_keywords = ['抽奖ID', '发起人', '参与人数', '截止日期', '中奖概率', '抽奖信息']
        for match in matches:
            keyword = match.strip()
            # 跳过系统字段
            if not any(sys_kw in keyword for sys_kw in system_keywords):
                print(f"[Lottery] Extracted participation keyword: '{keyword}'")
                return keyword
    
    return None

async def handle_lottery_auto_reply(client, event, lottery_config, message_text):
    """
    处理抽奖消息的自动回复。
    检测触发关键词 -> 提取参与关键词 -> 随机延时后回复
    """
    if not lottery_config or not lottery_config.get('enabled', False):
        return False
    
    trigger_keywords = lottery_config.get('trigger_keywords', ['抽奖信息', '抽奖ID'])
    
    # 检查消息是否包含触发关键词
    is_lottery_message = any(kw in message_text for kw in trigger_keywords)
    if not is_lottery_message:
        return False
    
    print(f"[Lottery] Lottery message detected in chat {event.chat_id}")
    
    # 提取参与关键词
    participation_keyword = extract_lottery_keyword(message_text)
    if not participation_keyword:
        print(f"[Lottery] Could not extract participation keyword from message")
        return False
    
    # 计算随机延时
    delay_min = lottery_config.get('reply_delay_min', 3)
    delay_max = lottery_config.get('reply_delay_max', 10)
    random_delay = random.uniform(delay_min, delay_max)
    
    print(f"[Lottery] Will reply with '{participation_keyword}' after {random_delay:.2f}s delay")
    
    # 异步发送回复（引用原消息）
    asyncio.create_task(
        send_delayed_reply(
            client, 
            event.chat_id, 
            participation_keyword, 
            reply_to=event.id, 
            delay=random_delay
        )
    )
    
    return True

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
    message_text = event.message.text or ""
    client = event.client

    # --- 1. 自动删除消息 ---
    auto_delete_rules = config.get('auto_delete_rules', [])
    for rule in auto_delete_rules:
        if not rule.get('enabled', True):
            continue
        rule_group_id = str(rule.get('group_id', ''))
        
        if rule_group_id == chat_id:
            try:
                delay = int(rule.get('delay', 60))
                token = rule.get('bot_token')
                if token:
                    asyncio.create_task(execute_auto_delete(token, chat_id, event.id, delay))
            except Exception as e:
                print(f"[Auto-Delete] Error scheduling delete: {e}")

    # --- 2. 消息转发 ---
    forward_rules = config.get('forward_rules', [])
    for rule in forward_rules:
        if not rule.get('enabled', True):
            continue
        
        source_id = str(rule.get('source_id', ''))
        if source_id == chat_id:
            target_id = rule.get('target_id')
            token = rule.get('bot_token')
            if target_id and token:
                asyncio.create_task(execute_forward(token, chat_id, target_id, event.id))

    # --- 3. 邮件/推送通知监听 ---
    group = next((g for g in config.get('groups', []) if g.get('id') == chat_id), None)
    if not group:
        return

    # --- 4. 抽奖自动参与 ---
    lottery_config = group.get('lottery')
    if lottery_config:
        await handle_lottery_auto_reply(client, event, lottery_config, message_text)

    sender = await event.message.get_sender()
    
    # --- 修复逻辑：兼容频道 (Channel) 发送者信息 ---
    sender_info = "Unknown Sender"
    if sender:
        # 如果是用户 (User)，有 first_name
        if hasattr(sender, 'first_name'):
            fn = sender.first_name or ''
            ln = sender.last_name or ''
            un = getattr(sender, 'username', 'N/A')
            sender_info = f"{fn} {ln} (@{un})".strip()
        # 如果是频道或群组 (Channel/Chat)，只有 title
        elif hasattr(sender, 'title'):
            title = sender.title
            un = getattr(sender, 'username', 'N/A')
            sender_info = f"{title} (@{un})".strip()
        # 其他情况
        else:
            sender_info = "Unknown Entity"
    # --- 修复逻辑结束 ---
    
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
                except (ValueError, TypeError):
                    delay_seconds = 5
                
                print(f"Keyword matched '{keyword_rule.get('word')}'. Scheduling reply in {delay_seconds}s...")
                # 传入 event.id 以进行引用回复
                asyncio.create_task(send_delayed_reply(client, event.chat_id, reply_content, reply_to=event.id, delay=delay_seconds))

    if not keyword_matched:
        notifiers_to_trigger.update(group.get('default_notifiers', []))

    if notifiers_to_trigger:
        print(f"Message from '{group_name}' triggered notifiers: {list(notifiers_to_trigger)}")
        await process_notifications(config, list(notifiers_to_trigger), subject, body)

# --- 网页爬虫工作线程 (无登录模式) ---
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
                                    
                                    msgs = soup.select('.tgme_widget_message_text')
                                    
                                    if msgs:
                                        latest_msg_html = msgs[-1]
                                        latest_text = latest_msg_html.get_text(separator='\n').strip()
                                        
                                        msg_hash = hashlib.md5(latest_text.encode('utf-8')).hexdigest()
                                        last_hash = scraper_state.get(username)
                                        
                                        if msg_hash != last_hash:
                                            print(f"[Scraper] New message found in @{username}")
                                            
                                            scraper_state[username] = msg_hash
                                            save_scraper_state(scraper_state)
                                            
                                            notifiers = channel.get('notifiers', [])
                                            
                                            display_name = channel.get('name')
                                            if not display_name:
                                                display_name = f"@{username}"
                                                
                                            subject = f"【TG订阅】{display_name} 更新"
                                            body = f"{latest_text}\n\n(来源: Web Preview)"
                                            
                                            await process_notifications(config, notifiers, subject, body)
                                    else:
                                        pass
                                else:
                                    print(f"[Scraper] Failed to fetch {url}, status: {resp.status}")

                    except Exception as e:
                        print(f"[Scraper] Error scraping {username}: {e}")
                    
                    await asyncio.sleep(random.uniform(2, 5))
            
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

# --- 定时任务处理逻辑 (依赖客户端) ---
async def scheduled_task_worker(client):
    """后台任务：每分钟检查定时任务。"""
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

# --- 主程序入口 ---
async def main():
    """主函数"""
    print("Starting services...")
    
    # 1. 始终启动网页爬虫任务 (独立于 TG 客户端)
    asyncio.create_task(scraper_task_worker())

    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    # 尝试从存储层加载 Session String
    saved_session_string = storage.load_data('session')

    # 情况 A: 环境变量缺失
    if not api_id or not api_hash:
        print("Warning: API_ID/HASH not set. Telegram Client mode disabled. Only Web Scraper will work.")
        while True:
            await asyncio.sleep(3600)
        return

    # 情况 B: Client 初始化 (使用 StringSession)
    if not saved_session_string:
        print("Notice: No saved session found. Initializing new login (StringSession)...")
        # 没有 Session 字符串，初始化为空，启动后需扫码
        client = TelegramClient(StringSession(), int(api_id), api_hash)
    else:
        print("Found saved session in storage. Logging in...")
        # 从字符串恢复 Session
        client = TelegramClient(StringSession(saved_session_string), int(api_id), api_hash)

    try:
        @client.on(events.NewMessage)
        async def event_handler(event):
            # 调用 handle_message
            await handle_message(event)

        print("Attempting to connect Telegram client...")
        await client.start()
        
        # 登录成功后，获取最新的 Session String 并保存到存储
        # 这样下次重启容器（尤其是 PaaS 上）就不会丢失登录状态了
        new_session_string = client.session.save()
        if new_session_string != saved_session_string:
            print("Session changed. Saving new session string to storage...")
            storage.save_data('session', new_session_string)
        
        print("Telegram client started successfully.")
        
        # 启动定时任务 (依赖 Client)
        client.loop.create_task(scheduled_task_worker(client))
        
        await client.run_until_disconnected()

    except Exception as e:
        print(f"Telegram client error: {e}")
        print("Client crashed or failed to start. Keeping process alive for Web Scraper...")
        while True:
            await asyncio.sleep(60)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user. Exiting.")
