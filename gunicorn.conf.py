# Gunicorn configuration file
import multiprocessing

# Use only 1 worker to minimize memory usage
workers = 1
threads = 1

# Maximum number of requests a worker will process before restarting
max_requests = 50
max_requests_jitter = 10

# Timeout for graceful worker restart
timeout = 300  # Increased timeout for audio processing

# Keep the worker alive for this many seconds after handling a request
keepalive = 5

# Log level
loglevel = 'info'

# Enable when debugging
reload = False

# Limit worker memory usage
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Worker class
worker_class = 'sync'

# Graceful timeout
graceful_timeout = 120

# Configure worker connections
worker_connections = 50
