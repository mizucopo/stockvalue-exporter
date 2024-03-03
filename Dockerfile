FROM python:3.12-alpine3.19

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.json .
COPY stockvalue.py .

RUN chmod 0600 config.json
ENV CONFIG_FILEPATH /app/config.json

CMD gunicorn -w 4 -b 0.0.0.0:9100 --chdir /app stockvalue:app
