# Base Image
FROM python:3.10-slim

WORKDIR /app

# Install system-level build tools and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libc6-dev \
    python3-dev \
    curl \
    && curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 - && \
    cd /usr/local/bin && ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Upgrade setuptools, virtualenv, and Poetry
RUN pip install --upgrade setuptools==65.5.1 virtualenv poetry

# Upgrade setuptools, virtualenv, and Poetry
RUN pip install blis==0.7.9 --no-cache-dir


# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Add Rasa Plus repository to Poetry
RUN poetry config repositories.rasa-plus https://europe-west3-python.pkg.dev/rasa-releases/rasa-plus-py/simple

# Pre-install shared dependencies (optional)
RUN poetry install --no-root


# Use build argument for Rasa Pro License
ARG RASA_PRO_LICENSE
ENV RASA_PRO_LICENSE=${RASA_PRO_LICENSE}

# Expose environment variables for both Rasa and actions
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV PYTHONUNBUFFERED=1