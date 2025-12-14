FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for XGBoost and other ML libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run sets PORT environment variable automatically
# Default to 8080 if not set
ENV PORT=8080
EXPOSE 8080

# Run FastAPI with uvicorn
# Cloud Run sets PORT environment variable automatically
# Use sh to properly expand $PORT
CMD sh -c "uvicorn src.dashboard_api:app --host 0.0.0.0 --port ${PORT:-8080}"

