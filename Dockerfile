FROM python:3.9

# Install system dependencies required for madmom and other packages
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir setuptools wheel

# Install Cython first (globally and in virtualenv)
RUN pip install --no-cache-dir cython==0.29.33
RUN /usr/local/bin/pip install --no-cache-dir cython==0.29.33

# Install dependencies one by one
RUN pip install --no-cache-dir flask==2.0.1
RUN pip install --no-cache-dir werkzeug==2.0.1
RUN pip install --no-cache-dir pydub==0.25.1
RUN pip install --no-cache-dir numpy==1.23.5
RUN pip install --no-cache-dir scipy==1.10.1
RUN CYTHON_BUILD_DIR=/tmp/cython pip install --no-cache-dir madmom==0.16.1
RUN pip install --no-cache-dir python-dotenv==0.19.0
RUN pip install --no-cache-dir gunicorn==20.1.0
RUN pip install --no-cache-dir beatmachine

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
