# gunicorn.conf.py — Production server configuration.
#
# Run from backend/ with:
#   gunicorn api.main:app -c gunicorn.conf.py

# Worker process count — 2x CPU cores + 1 is the standard heuristic
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"

# Bind
bind = "0.0.0.0:8000"

# Logging — write to stdout/stderr so the process manager (systemd, Docker, etc.)
# captures everything; structured JSON is handled by core/logging.py
accesslog = "-"
errorlog  = "-"
loglevel  = "info"

# Timeouts
timeout          = 120   # seconds before a worker is killed and restarted
keepalive        = 5     # seconds to wait for the next request on a keep-alive connection
graceful_timeout = 30    # seconds to finish in-flight requests on SIGTERM
