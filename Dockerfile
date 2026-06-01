FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/entrypoint.sh \
 && useradd -m -u 1000 app \
 && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
