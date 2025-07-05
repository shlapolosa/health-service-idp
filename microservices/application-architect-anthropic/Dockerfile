FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first
COPY ../shared-libs/ ./shared-libs/

# Install agent-common package
RUN pip install -e ./shared-libs/agent-common

# Copy requirements and install Python dependencies
COPY pyproject.toml application-architect-anthropic/poetry.lock* ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-root

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app:/app/shared-libs
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set working directory to src for execution
WORKDIR /app/src

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]