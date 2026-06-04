# Production-ready Gunicorn configuration for Railway
import os
workers = 2
worker_class = "sync"
bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"