# CoursePilot: one container serving the FastAPI API and the built React app.
#   docker build -t coursepilot .
#   docker run -p 8000:8000 coursepilot        -> http://localhost:8000

# ---- 1. build the frontend --------------------------------------------------
FROM node:20-alpine AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. runtime ---------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000
WORKDIR /app

COPY backend/pyproject.toml backend/
COPY backend/prereqpath backend/prereqpath
RUN pip install -e ./backend

# Only the parsed catalog and the verified overlays ship; the raw HTML cache does not.
COPY data/catalog data/catalog
COPY data/verified data/verified
COPY --from=web /app/frontend/dist frontend/dist

RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health', timeout=4)"
CMD ["sh", "-c", "exec uvicorn prereqpath.api:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
