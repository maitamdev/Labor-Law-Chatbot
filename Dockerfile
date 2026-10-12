# VietLabor AI - application image (Streamlit UI + RAG pipeline).
# The LLM (Ollama) and graph database (Neo4j) run as separate services, see
# docker-compose.yml. Corpus, indexes and the embedding model cache are mounted
# as volumes because they are large and gitignored.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libgl1/libglib2.0-0: required by opencv (pulled in by rapidocr-onnxruntime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch keeps the image ~2 GB smaller; embeddings/reranker run fine on
# CPU, the heavy LLM work happens in the Ollama container.
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.0.0"

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Inside the container the app must listen on all interfaces; docker-compose
# still publishes it on 127.0.0.1 only.
ENV VIETLABOR_HOST=0.0.0.0 \
    VIETLABOR_PORT=8501

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8501/_stcore/health || exit 1

CMD ["python", "-m", "app.main"]
