FROM node:22-alpine AS frontend
WORKDIR /src
RUN npm install --global pnpm@11.25.0
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./web/
RUN pnpm --dir web install --frozen-lockfile
COPY web ./web
ARG VITE_ANDROID_DOWNLOAD_URL="https://github.com/PedroSetti/SetRastrear/releases/download/v1.2.0/RastrearMB-debug.apk"
ENV VITE_HOSTED_BUILD=true
ENV VITE_ANDROID_DOWNLOAD_URL=$VITE_ANDROID_DOWNLOAD_URL
RUN pnpm --dir web run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WEB_DIST=/app/web/dist PORT=8080
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend .
COPY --from=frontend /src/web/dist /app/web/dist
RUN useradd --create-home --uid 10001 rastrear && chown -R rastrear:rastrear /app
USER rastrear
EXPOSE 8080
CMD ["sh", "-c", "python -m alembic upgrade head && exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --no-proxy-headers"]
