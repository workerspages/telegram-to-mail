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
        # 文件模式
        file_path = FILES.get(key)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if key == 'session':
                    f.write(data)
                else:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Storage] File Write Error ({key}): {e}")
