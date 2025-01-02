FROM python:3.9-slim

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Cython and numpy first
RUN pip install --no-cache-dir \
    cython==0.29.33 \
    numpy==1.23.5

# Copy requirements and install Python packages
COPY requirements.txt .
# Remove Cython and numpy from requirements since they're already installed
RUN grep -v "cython\|numpy" requirements.txt > requirements_filtered.txt && \
    pip install -r requirements_filtered.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
