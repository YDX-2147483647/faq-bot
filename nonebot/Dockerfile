FROM python:3-slim
WORKDIR /app

COPY pyproject.toml /app/
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -e . --no-cache-dir && \
    pip install "nb-cli>=1.4.2"

COPY .env /app/
