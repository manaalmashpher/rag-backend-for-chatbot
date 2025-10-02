# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching (builder stage only)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

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

# Final runtime stage
FROM python:3.11-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire built application (including requirements.txt and installed packages)
COPY --from=builder /app /app

# Expose port
EXPOSE 8000

# Start command
CMD ["python3", "run.py"]
