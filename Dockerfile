# ビルドステージ
FROM python:3.14.6-alpine AS builder

RUN apk add --no-cache \
    tzdata \
    && cp /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
    && echo "Asia/Tokyo" > /etc/timezone


# 実行ステージ
FROM python:3.14.6-alpine

ARG APP_UID=10001
ARG APP_GID=10001

COPY --from=builder /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
COPY --from=builder /etc/timezone /etc/timezone

RUN addgroup -S -g "${APP_GID}" appgroup \
    && adduser -S -D -u "${APP_UID}" -G appgroup -h /home/appuser appuser \
    && mkdir -p /home/appuser/.cache \
    && chown -R appuser:appgroup /home/appuser

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app
COPY .python-version \
     pyproject.toml \
     uv.lock \
     README.md \
     /app/

RUN apk add --no-cache --virtual .build-deps \
        build-base \
        libffi-dev \
    && pip install uv==0.11.28 \
    && uv sync --locked --no-dev --no-install-project \
    && apk del .build-deps

ENV PATH="/app/.venv/bin:$PATH"

COPY src/ /app/src/

RUN uv sync --locked --no-dev

RUN rm /app/.python-version \
    && rm /app/uv.lock

ENV HOME=/home/appuser \
    XDG_CACHE_HOME=/home/appuser/.cache

USER appuser:appgroup

EXPOSE 9100

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:9100", "--chdir", "/app", "src.main:web"]
