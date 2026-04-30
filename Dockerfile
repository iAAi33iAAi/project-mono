# ---------- Build stage ----------
FROM python:3.11-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/

EXPOSE 8000

CMD ["python", "-m", "src.main"]
