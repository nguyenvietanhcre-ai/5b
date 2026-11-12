FROM node:24-slim AS public-html
WORKDIR /build
COPY frontend ./frontend
COPY scripts/build-pages.cjs ./scripts/build-pages.cjs
RUN node scripts/build-pages.cjs /built-public python

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend ./backend
COPY frontend ./frontend
COPY scripts ./scripts
COPY --from=public-html /built-public ./frontend/public-pages
RUN mkdir /data && chown 65532:65532 /data
ENV MAM_TOAN_DATABASE=/data/5bmath-demo.sqlite3
USER 65532:65532
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
CMD ["python", "-m", "backend", "--host", "0.0.0.0", "--port", "8000"]
