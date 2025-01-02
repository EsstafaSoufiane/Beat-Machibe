FROM python:3.9-slim

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Cython first
RUN pip install cython==0.29.33

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
