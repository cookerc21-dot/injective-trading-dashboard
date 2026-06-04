# Production-ready Gunicorn configuration for Railway
workers = 2
worker_class = "sync"
bind = "0.0.0.0:$PORT"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = true
accesslog = "-"
errorlog = "-"
loglevel = "info"