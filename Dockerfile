FROM python:3.9-slim

WORKDIR /app

# Install system dependencies and optimizations
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
    cython==0.29.33 \
    numpy==1.23.5

# Set environment variables for better performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NUMBA_CACHE_DIR=/tmp/numba_cache
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1

# Copy requirements and install Python packages
COPY requirements.txt .
RUN grep -v "cython\|numpy" requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt

# Copy application code
COPY . .

# Create uploads directory with proper permissions
RUN mkdir -p uploads && chmod 777 uploads && \
    mkdir -p /tmp/numba_cache && chmod 777 /tmp/numba_cache

# Expose port 8080 for Railway
EXPOSE 8080

# Command to run the application with memory limit
CMD ["gunicorn", "--config", "gunicorn.conf.py", "--bind", "0.0.0.0:8080", "--worker-tmp-dir", "/dev/shm", "app:app"]
