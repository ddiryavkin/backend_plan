import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
worker_class = "uvicorn_worker.UvicornWorker"
