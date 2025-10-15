FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy MCP server code
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --frozen

# Expose HTTP port
EXPOSE 8000

# Run FastMCP server with HTTP transport
CMD ["uv", "run", "fastmcp", "run", "mcp_qbittorrent.server:mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
