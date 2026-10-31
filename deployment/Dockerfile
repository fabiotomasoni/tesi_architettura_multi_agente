FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app
COPY pyproject.toml requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY gateway ./gateway
COPY services ./services
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --no-create-home app
USER 10001:10001
