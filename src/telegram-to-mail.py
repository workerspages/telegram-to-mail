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
# 新增：用于记录定时任务当天是否已执行的状态文件
STATE_FILE = os.path.join(SESSION_DIR, 'schedule_state.json')

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

# --- 辅助函数 ---
def get_bark_details(config, bark_id):
    """根据 Bark ID，从配置中获取对应的 token 和 server_url"""
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
    """根据 Pushplus ID，从配置中获取对应的 token"""
    notifiers_config = config.get('notifiers', {})
    if 'pushplus' in notifiers_config:
        for pushplus_notifier in notifiers_config['pushplus']:
            if pushplus_notifier.get('id') == pushplus_id:
                return pushplus_notifier.get('token')
    return None

# --- 自动回复功能 ---
async def send_delayed_reply(client, chat_id, message, delay=5):
    """
    延迟指定秒数后发送回复消息。
    :param delay: 延迟时间（秒），默认 5 秒
    """
    if delay > 0:
        await asyncio.sleep(delay)
    try:
        await client.send_message(chat_id, message)
        print(f"[Auto-Reply] Sent reply to {chat_id} after {delay}s: {message}")
    except Exception as e:
        print(f"[Auto-Reply] Failed to send reply to {chat_id}: {e}")

# --- 核心消息处理逻辑 ---
async def process_notifications(config, notifiers_list, subject, body):
    """处理并发送一组通知，包含错误捕获逻辑。"""
    for nid in notifiers_list:
        try:
            if nid.startswith('bark'):
                bark_details = get_bark_details(config, nid)
                if bark_details and bark_details.get('token'):
                    server_url = bark_details.get('server_url') or "https://api.day.app"
                    await send_bark(server_url, bark_details['token'], subject, body)

            # ★★★ 修复点：此前写的是 'pp'，但前端生成的ID是 'pushplus' 开头 ★★★
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
    """处理新消息事件"""
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
    subject = f"【Telegram】来自 {group_name} 的新消息"
    body = f"发信人: {sender_info}\n\n{message_text}"

    notifiers_to_trigger = set()
    keyword_matched = False

    client = event.client

    # 检查关键字规则
    for keyword_rule in group.get('keywords', []):
        if keyword_rule.get('word') and keyword_rule.get('word') in message_text:
            # 1. 触发通知
            notifiers_to_trigger.update(keyword_rule.get('notifiers', []))
            keyword_matched = True
            
            # 2. 触发自动回复
            reply_content = keyword_rule.get('reply_content')
            if reply_content:
                # 获取配置的延迟时间，如果未设置或无效，默认为 5 秒
                try:
                    delay_seconds = float(keyword_rule.get('reply_delay', 5))
                except (ValueError, TypeError):
                    delay_seconds = 5
                
                print(f"Keyword matched '{keyword_rule.get('word')}'. Scheduling reply in {delay_seconds}s...")
                asyncio.create_task(send_delayed_reply(client, event.chat_id, reply_content, delay_seconds))

    # 如果没有关键字匹配，则使用默认推送规则
    if not keyword_matched:
        notifiers_to_trigger.update(group.get('default_notifiers', []))

    # 发送通知
    if notifiers_to_trigger:
        print(f"Message from '{group_name}' triggered notifiers: {list(notifiers_to_trigger)}")
        await process_notifications(config, list(notifiers_to_trigger), subject, body)
    else:
        print(f"Message from '{group_name}' did not trigger any notifiers.")

# --- 定时任务处理逻辑 (随机时间版) ---
async def scheduled_task_worker(client):
    """
    后台任务：每分钟检查定时任务。
    支持在设定的 [Start, End] 时间段内随机触发。
    """
    print("Scheduled task worker started (Randomized Mode).")
    
    # 内存中的随机目标时间缓存
    daily_random_targets = {}
    last_check_minute = None

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            current_minute_str = now.strftime("%H:%M")
            
            # 防抖
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
                    
                    # 构造任务唯一签名
                    task_sig = f"{target}_{msg}_{task.get('time_start')}_{task.get('time_end')}_{idx}"
                    
                    # 检查今天是否已运行
                    if state.get(task_sig) == today_str:
                        continue

                    # 解析时间段
                    t_start_str = task.get('time_start') or task.get('time') or "08:00"
                    t_end_str = task.get('time_end') or task.get('time') or "08:00"
                    
                    try:
                        h_s, m_s = map(int, t_start_str.split(':'))
                        h_e, m_e = map(int, t_end_str.split(':'))
                        dt_start = now.replace(hour=h_s, minute=m_s, second=0, microsecond=0)
                        dt_end = now.replace(hour=h_e, minute=m_e, second=0, microsecond=0)
                        
                        # 忽略跨天或无效时间
                        if dt_end < dt_start: continue
                        if now < dt_start: continue
                        if now > dt_end: continue
                        
                        # 生成或获取今日随机目标时间
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
                            print(f"[Schedule] Task {idx} target set to {random_dt.strftime('%H:%M:%S')} (Range: {t_start_str}-{t_end_str})")
                        
                        target_dt = daily_random_targets[target_key]
                        
                        # 到达时间触发
                        if now >= target_dt:
                            try:
                                entity = int(target) if target.lstrip('-').isdigit() else target
                                await client.send_message(entity, msg)
                                print(f"[Schedule] Executed task {idx}: Sent '{msg}' to {target}")
                                
                                state[task_sig] = today_str
                                save_state(state)
                                
                                if target_key in daily_random_targets:
                                    del daily_random_targets[target_key]
                                    
                            except Exception as e:
                                print(f"[Schedule] Failed to send to {target}: {e}")
                                
                    except ValueError:
                        print(f"[Schedule] Invalid time format for task {idx}")
                        continue

            last_check_minute = current_minute_str
            
            # 对齐时间
            seconds_to_sleep = 60 - datetime.now().second
            await asyncio.sleep(seconds_to_sleep)
            
        except Exception as e:
            print(f"Error in scheduled worker: {e}")
            await asyncio.sleep(60)

# --- 主程序入口 ---
async def main():
    """主函数，初始化并运行客户端"""
    print("Starting Telegram client...")
    
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')

    if not api_id or not api_hash:
        print("Error: API_ID and API_HASH environment variables must be set.")
        return

    try:
        api_id = int(api_id)
    except ValueError:
        print("Error: API_ID must be an integer.")
        return

    client = TelegramClient(SESSION_NAME, api_id, api_hash)
    
    @client.on(events.NewMessage)
    async def event_handler(event):
        await handle_message(event)

    try:
        await client.start()
        print("Telegram client started successfully.")
        
        # 启动定时任务后台协程
        client.loop.create_task(scheduled_task_worker(client))
        
        await client.run_until_disconnected()
    except Exception as e:
        print(f"An error occurred while running the client: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()
        print("Telegram client disconnected.")

if __name__ == '__main__':
    # 确保持久化目录存在
    if not os.path.exists(SESSION_DIR):
        os.makedirs(SESSION_DIR)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user. Exiting.")
