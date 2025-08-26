# Dockerfile — Backend (FastAPI + Uvicorn)
FROM python:3.11-slim

WORKDIR /app
# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc git build-essential && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install Python deps (backend + minimal frontend requirements for static export)
RUN pip install --upgrade pip
RUN pip install -r voyagerai/backend/requirements.txt

# Expose port
ENV PORT 8000
EXPOSE 8000

# Default command
CMD ["uvicorn", "voyagerai.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio", "--lifespan", "on"]
