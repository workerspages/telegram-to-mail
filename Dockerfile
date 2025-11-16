# 使用轻量 python 官方镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖和 msmtp
RUN apt-get update && apt-get install -y msmtp ca-certificates && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY ./src/ .

# 复制并设置 entrypoint 脚本
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# 设置入口点
ENTRYPOINT ["entrypoint.sh"]

# 启动默认命令，使用 supervisord 同时启动两个服务
CMD ["sh", "-c", "python web_manager.py & python -u telegram-to-mail.py"]
