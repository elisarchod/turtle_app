FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy MCP server code
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies from pyproject.toml
RUN uv venv && \
    uv pip install aiohttp>=3.12.15 fastmcp>=2.12.4 pydantic>=2.11.9 pydantic-settings>=2.11.0

# Expose HTTP port
EXPOSE 8000

# Set PYTHONPATH so module can be found
ENV PYTHONPATH=/app/src

# Run FastMCP server with HTTP transport
CMD [".venv/bin/fastmcp", "run", "mcp_qbittorrent.server:mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
