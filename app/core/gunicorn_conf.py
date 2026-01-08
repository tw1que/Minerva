import os

bind = "0.0.0.0:8000"
worker_class = "uvicorn.workers.UvicornWorker"
workers = max(2, (os.cpu_count() or 1) * 2 + 1)
accesslog = "-"
errorlog = "-"
timeout = 60
