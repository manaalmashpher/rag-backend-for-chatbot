# ---------- FRONTEND: build Vite app ----------
    FROM node:20-bookworm-slim AS fe-builder
    WORKDIR /fe
    
    # Copy only what the build needs for good caching
    COPY package*.json ./
    COPY tsconfig*.json ./
    COPY vite.config.* .
    COPY index.html ./
    COPY src ./src
    
    RUN npm ci --ignore-scripts && npm run build
    
    # ---------- PYTHON: build deps in a venv ----------
    FROM python:3.11-slim-bookworm AS py-builder
    ENV PIP_NO_CACHE_DIR=1 \
        PIP_DISABLE_PIP_VERSION_CHECK=1 \
        PYTHONDONTWRITEBYTECODE=1
    
    # keep builder minimal; psycopg2-binary doesn't need dev libs
    RUN apt-get update && apt-get install -y --no-install-recommends gcc \
     && rm -rf /var/lib/apt/lists/*
    
    WORKDIR /app
    COPY requirements.txt .
    
    # Create compact venv
    RUN python -m venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    
    # Install CPU-only torch first, then the rest (excluding torch to avoid re-pulling)
    RUN grep -vE '^torch(==|>=|~=)' requirements.txt > requirements.notorch.txt \
     && pip install --no-cache-dir --no-compile --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 \
     && pip install --no-cache-dir --no-compile -r requirements.notorch.txt
    
    # ---------- RUNTIME ----------
    FROM python:3.11-slim-bookworm AS runtime
    ENV PATH="/opt/venv/bin:$PATH" \
        PYTHONUNBUFFERED=1 \
        HF_HOME=/cache/hf \
        TRANSFORMERS_CACHE=/cache/hf
    
    # Small runtime libs only
    RUN apt-get update && apt-get install -y --no-install-recommends \
        curl libpq5 \
     && rm -rf /var/lib/apt/lists/*
    
    WORKDIR /app
    
    # Bring in venv and app code
    COPY --from=py-builder /opt/venv /opt/venv
    
    # Copy only what the backend needs
    # (adjust if you have extra runtime files)
    COPY app ./app
    COPY run.py .
    COPY requirements.txt . 
    
    # Copy built frontend to /app/dist (FastAPI can serve it)
    COPY --from=fe-builder /fe/dist ./dist
    
    # Cache dir for models; attach a Railway volume here if possible
    RUN mkdir -p /cache/hf
    
    EXPOSE 8000
    CMD ["python", "run.py"]
    