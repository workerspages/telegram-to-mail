import os
import json
import pymysql
from telethon.sessions import StringSession

# 环境变量读取数据库配置
DB_HOST = os.getenv('MARIADB_HOST')
DB_PORT = int(os.getenv('MARIADB_PORT', 3306))
DB_USER = os.getenv('MARIADB_USER')
DB_PASS = os.getenv('MARIADB_PASSWORD')
DB_NAME = os.getenv('MARIADB_DATABASE', 'telegram_bot')

# 检查是否启用数据库模式
USE_DB = all([DB_HOST, DB_USER, DB_PASS])

# 本地文件路径定义
# 优先使用 /app/data 目录（Docker 环境）
# 兼容符号链接方式（entrypoint.sh 创建）和直接访问方式
if os.path.exists('/app/data'):
    DATA_DIR = '/app/data'
elif os.path.exists('./data'):
    DATA_DIR = './data'
else:
    DATA_DIR = '.'

FILES = {
    'config': os.path.join(DATA_DIR, 'config.json'),
    'schedule_state': os.path.join(DATA_DIR, 'schedule_state.json'),
    'scraper_state': os.path.join(DATA_DIR, 'scraper_state.json'),
    'session': os.path.join(DATA_DIR, 'session.string') # 本地模式下把session string存文件方便迁移
}

# SQLite session 文件可能的路径（Telethon 默认格式）
# 支持多个位置：优先 session_data 子目录，其次 data 根目录
SESSION_FILE_PATHS = [
    os.path.join(DATA_DIR, 'session_data', 'telegram.session'),  # 子目录
    os.path.join(DATA_DIR, 'telegram.session'),                   # 根目录
]

def get_session_file_path():
    """
    检查 SQLite session 文件是否存在，存在则返回路径，否则返回 None
    支持的位置: /app/data/session_data/telegram.session 或 /app/data/telegram.session
    """
    for path in SESSION_FILE_PATHS:
        if os.path.exists(path):
            return path
    return None

def get_session_from_env():
    """
    从环境变量读取 Base64 编码的 session string
    环境变量名: SESSION_STRING
    返回: 解码后的 session string，如果未设置或解码失败则返回 None
    """
    import base64
    session_b64 = os.getenv('SESSION_STRING')
    if not session_b64:
        return None
    
    try:
        # 解码 Base64
        session_string = base64.b64decode(session_b64).decode('utf-8')
        print("[Storage] Found SESSION_STRING in environment variable.")
        return session_string
    except Exception as e:
        print(f"[Storage] Failed to decode SESSION_STRING: {e}")
        return None

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset='utf8mb4', autocommit=True
    )

def init_storage():
    """初始化：如果用数据库，自动建表"""
    if not USE_DB:
        print("[Storage] Using Local File System mode.")
        return

    print(f"[Storage] Using MariaDB mode ({DB_HOST}).")
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 创建一个简单的键值对表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key VARCHAR(50) PRIMARY KEY,
                    setting_value LONGTEXT
                )
            """)
        conn.close()
    except Exception as e:
        print(f"[Storage] DB Init Error: {e}")

def load_data(key, default_value=None):
    """读取数据 (通用)"""
    if USE_DB:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT setting_value FROM app_settings WHERE setting_key=%s", (key,))
                result = cursor.fetchone()
            conn.close()
            if result:
                # Session 是纯字符串，其他是 JSON
                if key == 'session':
                    return result[0]
                return json.loads(result[0])
            return default_value
        except Exception as e:
            print(f"[Storage] Load Error ({key}): {e}")
            return default_value
    else:
        # 文件模式
        file_path = FILES.get(key)
        if not file_path or not os.path.exists(file_path):
            return default_value
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if key == 'session':
                    return content
                return json.loads(content)
        except Exception:
            return default_value

def save_data(key, data):
    """保存数据 (通用)"""
    if USE_DB:
        try:
            # Session 存字符串，其他转 JSON
            value_to_store = data if key == 'session' else json.dumps(data, ensure_ascii=False)
            
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO app_settings (setting_key, setting_value) 
                    VALUES (%s, %s) 
                    ON DUPLICATE KEY UPDATE setting_value=%s
                """, (key, value_to_store, value_to_store))
            conn.close()
        except Exception as e:
            print(f"[Storage] Save Error ({key}): {e}")
    else:
        # 文件模式 - 使用原子写入防止并发问题
        file_path = FILES.get(key)
        temp_path = file_path + '.tmp'
        try:
            # 先写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                if key == 'session':
                    f.write(data)
                else:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # 确保写入磁盘
            
            # 然后原子性地重命名（替换）目标文件
            os.replace(temp_path, file_path)
        except Exception as e:
            print(f"[Storage] File Write Error ({key}): {e}")
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

