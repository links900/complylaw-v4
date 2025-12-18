web: gunicorn core.asgi:application --bind 0.0.0.0:$PORT --workers 2 -k uvicorn.workers.UvicornWorker
worker: celery -A core worker --loglevel=info --concurrency=2