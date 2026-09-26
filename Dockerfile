FROM python:3.12-slim

WORKDIR /app/backend

# ENVIRONMENT is deliberately NOT set here (defaults to "development" --
# see app/core/config.py). Setting it to "production" makes the app
# refuse to boot at all without real UPSTOX_API_KEY/UPSTOX_API_SECRET
# broker credentials (a deliberate safety check against accidentally
# running live-trading mode on placeholder keys) -- paper trading, which
# is all this deployment needs, doesn't require them. Override via this
# host's own env var settings if you later add real broker credentials.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

# System deps needed to build a couple of the scientific-computing wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# requirements-core.txt (API + classical ML, no deep learning) keeps the
# image small and the build fast -- the right default for a free-tier
# host. Swap in requirements.txt (adds torch/transformers/torch-geometric)
# if you need the deep-learning models and have the resources for it.
COPY backend/requirements-core.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-core.txt

COPY backend/ /app/backend/

RUN useradd --create-home --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers"]
