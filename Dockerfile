FROM python:3.10-slim
WORKDIR /app

# ★★★ 修改点：在安装依赖时，额外添加 wget 用于下载 ★★★
RUN apt-get update && apt-get install -y msmtp ca-certificates wget && rm -rf /var/lib/apt/lists/*

# ★★★ 新增：下载并安装 Cloudflare Tunnel 客户端 (cloudflared) ★★★
RUN wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && \
    dpkg -i cloudflared-linux-amd64.deb && \
    rm cloudflared-linux-amd64.deb

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY ./src/ .
# 将默认配置复制到一个专门的模板位置
COPY ./src/config.json /app/config.json.default

# 复制并授权启动脚本
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
CMD ["sh", "-c", "python web_manager.py & python -u telegram-to-mail.py"]
