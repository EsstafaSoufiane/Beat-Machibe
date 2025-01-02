# Gunicorn configuration file
import multiprocessing

# Number of worker processes for handling requests
workers = 2  # Reduced number of workers to conserve memory
threads = 1

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50

# Timeout for graceful worker restart
timeout = 120  # Increased timeout for audio processing

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
