FROM python:3.9-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Cython first
RUN pip install --no-cache-dir cython==0.29.33

# Install numpy separately
RUN pip install --no-cache-dir numpy==1.23.5

# Copy requirements and install remaining packages
COPY requirements.txt .
RUN grep -v "cython\|numpy" requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    rm -rf ~/.cache/pip/*

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p uploads temp && \
    chmod 777 uploads temp

# Set environment variables for minimal resource usage
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV NUMBA_NUM_THREADS=1
ENV MALLOC_TRIM_THRESHOLD_=100000
ENV PYTHONMALLOC=malloc
ENV PYTHONMALLOCSTATS=0

# Expose port
EXPOSE 8080

# Run with minimal resources
CMD gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 2 \
    --timeout 300 \
    --max-requests 100 \
    --max-requests-jitter 10 \
    --worker-tmp-dir /dev/shm \
    --worker-class gthread \
    --limit-request-line 4094 \
    --limit-request-fields 100 \
    --limit-request-field_size 8190 \
    app:app
