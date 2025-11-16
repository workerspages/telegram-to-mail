FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y msmtp ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY ./src/ .
# ★★★ 新增：将默认配置复制到一个专门的模板位置 ★★★
COPY ./src/config.json /app/config.json.default

# 复制并授权启动脚本
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
CMD ["sh", "-c", "python web_manager.py & python -u telegram-to-mail.py"]
