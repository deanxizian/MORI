FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
WORKDIR /app
COPY backend/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock && useradd --uid 10001 --create-home mori
COPY contracts /app/contracts
COPY simulation /app/simulation
COPY backend /app/backend
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
ENV MORI_DATA_DIR=/data PYTHONDONTWRITEBYTECODE=1
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=2)"
CMD ["python","-m","uvicorn","backend.mori.app:create_app","--factory","--host","0.0.0.0","--port","8765","--ws-max-size","4096"]
