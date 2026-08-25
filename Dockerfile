FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     TZ=Europe/Rome

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     ca-certificates curl tzdata     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p /app/data/photos

EXPOSE 8090

CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8090", "--timeout", "120", "app.main:app"]
