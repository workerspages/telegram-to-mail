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
if [ ! -f "$PERSISTENT_CONFIG_FILE" ]; then
  echo "Config file not found in persistent storage. Initializing from default."
  cp "$DEFAULT_CONFIG_FILE" "$PERSISTENT_CONFIG_FILE"
fi

# --- 核心逻辑：建立符号链接 ---
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


# ★★★ 新增：可选的 Cloudflare Tunnel 功能 ★★★
# 检查 TUNNEL_TOKEN 环境变量是否设置且不为空
if [ -n "$TUNNEL_TOKEN" ]; then
  echo "TUNNEL_TOKEN detected. Starting Cloudflare Tunnel..."
  # 在后台启动 Cloudflare Tunnel，并将日志输出到标准输出
  # --no-autoupdate 是在容器中运行的最佳实践
  # Tunnel 会将流量指向 Flask 服务的 5000 端口
  cloudflared tunnel --no-autoupdate --url http://localhost:5000 run --token "$TUNNEL_TOKEN" &
else
  echo "TUNNEL_TOKEN not set. Skipping Cloudflare Tunnel."
fi


# 执行 Docker CMD 中定义的命令
exec "$@"
