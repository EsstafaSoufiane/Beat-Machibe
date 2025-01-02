FROM python:3.9-slim

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    ffmpeg \
    libsndfile1 \
    pkg-config \
    libpython3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    gcc \
    g++ \
    gfortran \
    musl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir setuptools wheel

# Install Cython first
RUN pip install --no-cache-dir cython==0.29.33

# Install dependencies with optimized settings
RUN pip install --no-cache-dir \
    flask==2.0.1 \
    werkzeug==2.0.1 \
    pydub==0.25.1 \
    numpy==1.23.5 \
    scipy==1.10.1 \
    gunicorn==20.1.0 \
    beatmachine

# Install madmom with optimized settings
RUN CYTHON_BUILD_DIR=/tmp/cython pip install --no-cache-dir madmom==0.16.1

# Copy application code
COPY . .

# Create uploads directory with proper permissions
RUN mkdir -p uploads && chmod 777 uploads

# Create a swap file to help with memory management
RUN dd if=/dev/zero of=/swapfile bs=1M count=1024 && \
    chmod 600 /swapfile && \
    mkswap /swapfile && \
    echo "/swapfile swap swap defaults 0 0" >> /etc/fstab

# Expose port
EXPOSE 8000

# Set environment variables for memory management
ENV PYTHONUNBUFFERED=1
ENV PYTHONMALLOC=malloc
ENV MALLOC_TRIM_THRESHOLD_=65536
ENV PYTHONOPTIMIZE=2
ENV MADMOM_AUDIO_BACKEND=ffmpeg

# Command to run the application with memory limits
CMD swapon /swapfile && \
    gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --timeout 300 \
    --worker-class sync \
    --max-requests 1 \
    --max-requests-jitter 0 \
    --preload \
    --worker-tmp-dir /dev/shm \
    --limit-request-line 0 \
    --limit-request-fields 32768 \
    app:app
