#!/bin/sh
if [ -z "$MSMTP_HOST" ] || [ -z "$MSMTP_USER" ] || [ -z "$MSMTP_PASSWORD" ] || [ -z "$MSMTP_FROM" ]; then
  echo "错误：一个或多个 msmtp 环境变量未设置。"
  echo "请在 docker-compose.yml 中定义 MSMTP_HOST, MSMTP_USER, MSMTP_PASSWORD, MSMTP_FROM。"
  exit 1
fi
cat <<EOF > /etc/msmtprc
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /dev/stdout
account        default
host           ${MSMTP_HOST}
port           ${MSMTP_PORT:-587}
from           ${MSMTP_FROM}
user           ${MSMTP_USER}
password       ${MSMTP_PASSWORD}
EOF
chmod 600 /etc/msmtprc
exec "$@"
