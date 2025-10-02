# Use Python 3.11 alpine image for much smaller size
FROM python:3.11-alpine

# Install system dependencies for Alpine
RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    curl \
    nodejs \
    npm \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy package files
COPY package*.json ./

# Install Node.js dependencies (including dev dependencies for build)
RUN npm install

# Copy source code
COPY . .

# Build frontend
RUN npm run build

# Clean up to reduce image size
RUN npm cache clean --force \
    && rm -rf /root/.npm \
    && rm -rf /tmp/*

# Expose port
EXPOSE 8000

# Start command
CMD ["python3", "run.py"]
