FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure /data exists even without a Railway volume (volume mount will shadow it)
RUN mkdir -p /data

# Safe defaults — override in Railway dashboard for live trading
ENV DRY_RUN=true \
    TRADING_ENABLED=false \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite+aiosqlite:////data/trader.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
