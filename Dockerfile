# ビルドステージ
FROM python:3.14.6-alpine AS builder

RUN apk add --no-cache \
    tzdata \
    && cp /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
    && echo "Asia/Tokyo" > /etc/timezone


# 実行ステージ
FROM python:3.14.6-alpine

COPY --from=builder /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
COPY --from=builder /etc/timezone /etc/timezone

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app
COPY .python-version \
     pyproject.toml \
     uv.lock \
     README.md \
     /app/

RUN pip install uv==0.11.28 \
    && uv sync --locked --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH"

COPY src/ /app/src/

RUN uv sync --locked --no-dev

RUN rm /app/.python-version \
    && rm /app/uv.lock

EXPOSE 9100

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:9100", "--chdir", "/app", "src.main:web"]
