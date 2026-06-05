FROM python:3.9-slim

WORKDIR /app

# 🔥 Install kubectl + dependencies
RUN apt-get update && apt-get install -y curl gcc \
    && curl -LO "https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# ⚠️ IMPORTANT: DO NOT use non-root (kubectl needs access)
# REMOVE appuser (this is critical)
# RUN useradd -m appuser
# USER appuser

EXPOSE 5003

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:5003/health || exit 1

CMD ["python", "app.py"]