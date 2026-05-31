# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/client
COPY client/package*.json ./
RUN npm install
COPY client/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

# Install Python dependencies
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/ ./server/

# Copy built frontend
COPY --from=frontend-builder /app/client/dist ./client/dist

# Create data directory
RUN mkdir -p /data/uploads

# Run as non-root
RUN useradd --create-home appuser
RUN chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8100

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8100", "--timeout-keep-alive", "5"]
