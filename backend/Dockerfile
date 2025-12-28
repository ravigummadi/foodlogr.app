# FoodLogr MCP Server - Cloud Run Dockerfile

FROM python:3.12-slim

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY src/ ./src/

# Cloud Run sets PORT env var
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV FIRESTORE_DATABASE=foodlogr

# Run the MCP server with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
