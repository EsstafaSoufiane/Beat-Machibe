FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Cython first
RUN pip install --no-cache-dir cython==0.29.33

# Install numpy separately (required for madmom)
RUN pip install --no-cache-dir numpy==1.23.5

# Copy requirements and install remaining Python packages
COPY requirements.txt .
RUN grep -v "cython\|numpy" requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt

# Copy application code
COPY . .

# Create required directories with proper permissions
RUN mkdir -p uploads temp && \
    chmod 777 uploads temp

# Set environment variables for better performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV NUMBA_NUM_THREADS=1

# Expose port
EXPOSE 8080

# Run with gunicorn using limited resources
CMD gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 2 \
    --timeout 300 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --worker-tmp-dir /dev/shm \
    --worker-class gthread \
    app:app
