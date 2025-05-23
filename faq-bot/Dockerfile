FROM python:3-slim
WORKDIR /app

COPY pyproject.toml /app/
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -e . --no-cache-dir

COPY faq_bot /app/faq_bot/
COPY .env /app/
