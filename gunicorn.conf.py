# Gunicorn configuration for Render free tier (512 MB RAM)
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8050')}"
workers = 1
threads = 4
timeout = 120
preload_app = True
accesslog = "-"
