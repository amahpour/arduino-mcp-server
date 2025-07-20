# Dockerfile for arduino-mcp-server
FROM python:3.12-bullseye

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl git udev && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Install arduino-cli
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
ENV PATH="/root/bin:$PATH"

# Add udev rules for Arduino (optional, for USB access)
COPY 99-arduino.rules /etc/udev/rules.d/99-arduino.rules
RUN udevadm control --reload-rules || true

# Set workdir and copy project
WORKDIR /app
COPY . .

# Install Python dependencies
RUN poetry install --no-interaction --no-root

# Expose MCP server as the default entrypoint
ENTRYPOINT ["poetry", "run", "arduino-mcp-server"]

# Usage:
# docker build -t arduino-mcp-server .
# docker run --rm --device=/dev/ttyACM0 --env LOG_LEVEL=INFO arduino-mcp-server 