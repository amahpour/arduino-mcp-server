# Multi-stage Dockerfile for arduino-mcp-server
FROM python:3.12-slim as base

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        git \
        udev \
        && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Install arduino-cli
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
ENV PATH="/root/bin:$PATH"

# Development stage for building
FROM base as builder

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-root --only=main

# Production stage
FROM base as production

# Add udev rules for Arduino (optional, for USB access)
COPY 99-arduino.rules /etc/udev/rules.d/99-arduino.rules
RUN udevadm control --reload-rules || true

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY sketches/ ./sketches/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash arduino && \
    chown -R arduino:arduino /app
USER arduino

# Set default command that can be overridden
CMD ["arduino-mcp-server"]

# Usage:
# docker build -t arduino-mcp-server .
# docker run --rm --device=/dev/ttyACM0 --env LOG_LEVEL=INFO arduino-mcp-server
# docker run --rm --device=/dev/ttyACM0 arduino-mcp-server --help 