#!/bin/sh
cat <<EOF > /etc/msmtprc
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /dev/stdout
# 以上参数将在运行时动态覆盖
EOF
chmod 600 /etc/msmtprc
exec "$@"
