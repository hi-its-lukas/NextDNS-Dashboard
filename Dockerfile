FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY docker-requirements.txt .
RUN pip install --no-cache-dir -r docker-requirements.txt

COPY app.py .
RUN mkdir -p .streamlit
COPY .streamlit/docker-config.toml .streamlit/config.toml

EXPOSE 5050

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5050/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=5050", "--server.address=0.0.0.0"]
