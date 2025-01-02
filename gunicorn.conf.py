# Gunicorn configuration file
import multiprocessing

# Worker settings
workers = 1
threads = 2
worker_class = 'sync'
worker_connections = 50

# Timeouts
timeout = 600  # 10 minutes
graceful_timeout = 300  # 5 minutes
keepalive = 5

# Restart workers periodically to prevent memory leaks
max_requests = 100
max_requests_jitter = 10

# Log level
loglevel = 'info'

# Enable when debugging
reload = False

# Startup settings
preload_app = True
capture_output = True
enable_stdio_inheritance = True

# Limit worker memory usage
limit_request_line = 0  # unlimited
limit_request_fields = 100
limit_request_field_size = 0  # unlimited
