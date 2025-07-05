FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install agent-common wheel
COPY shared-libs/agent-common/dist/*.whl ./
RUN pip install *.whl

# Copy requirements and install Python dependencies
COPY business-architect-anthropic/pyproject.toml business-architect-anthropic/poetry.lock* ./
RUN pip install poetry &&     poetry config virtualenvs.create false &&     poetry install --only main --no-root

# Copy application code
COPY business-architect-anthropic/src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
