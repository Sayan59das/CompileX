FROM python:3.11-slim

WORKDIR /app

# System dependencies for code execution sandbox
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-jdk \
    nodejs \
    npm \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# PORT env var: Render injects $PORT
ENV PORT=10000

EXPOSE $PORT

# Start server
CMD ["bash", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
