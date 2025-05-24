FROM python:3-slim
WORKDIR /app

COPY pyproject.toml /app/
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -e . --no-cache-dir

# Uncomment the following lines if you are not using `../docker-compose.yml`.
# COPY .env /app/
# COPY faq_bot /app/faq_bot/
