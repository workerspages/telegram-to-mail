FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y msmtp ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./src/ .
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
CMD ["sh", "-c", "python web_manager.py & python -u telegram-to-mail.py"]
