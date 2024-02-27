FROM python:3.12-alpine3.19

RUN apk add --no-cache \
    tzdata=2023d-r0 \
  && cp /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
  && echo "Asia/Tokyo" > /etc/timezone

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.json .
COPY stockvalue.py .

RUN chmod 0600 config.json
ENV CONFIG_FILEPATH /app/config.json

CMD gunicorn -w 4 -b 0.0.0.0:9100 --chdir /app stockvalue:app
