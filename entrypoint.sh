#!/bin/sh

# 定义持久化数据和会话的目录
PERSISTENT_DATA_DIR="/app/data"
PERSISTENT_CONFIG_FILE="$PERSISTENT_DATA_DIR/config.json"
PERSISTENT_SESSION_DIR="$PERSISTENT_DATA_DIR/session_data"

# 定义应用期望的路径
APP_CONFIG_FILE="/app/config.json"
APP_SESSION_DIR="/app/session_data"
DEFAULT_CONFIG_FILE="/app/config.json.default"

# 确保持久化目录存在
mkdir -p "$PERSISTENT_DATA_DIR"
mkdir -p "$PERSISTENT_SESSION_DIR"

# --- 核心逻辑：配置文件初始化 ---
# 如果持久化目录中没有配置文件，则从模板复制一份
if [ ! -f "$PERSISTENT_CONFIG_FILE" ]; then
  echo "Config file not found in persistent storage. Initializing from default."
  cp "$DEFAULT_CONFIG_FILE" "$PERSISTENT_CONFIG_FILE"
fi

# --- 核心逻辑：建立符号链接 ---
# 删除应用目录下的旧文件/链接，然后创建新的链接指向持久化位置
# 这样 Python 代码无需任何改动
rm -rf "$APP_CONFIG_FILE"
ln -s "$PERSISTENT_CONFIG_FILE" "$APP_CONFIG_FILE"

rm -rf "$APP_SESSION_DIR"
ln -s "$PERSISTENT_SESSION_DIR" "$APP_SESSION_DIR"


# --- msmtp 配置文件 (原逻辑保留) ---
cat <<EOF > /etc/msmtprc
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /dev/stdout
EOF
chmod 600 /etc/msmtprc

# 执行 Docker CMD 中定义的命令
exec "$@"
