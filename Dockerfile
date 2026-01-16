FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY docker-requirements.txt .
RUN pip install --no-cache-dir -r docker-requirements.txt

COPY app.py .
COPY .streamlit .streamlit

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=5000", "--server.address=0.0.0.0"]
