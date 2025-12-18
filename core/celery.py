# core/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# FORCE SOLO ON WINDOWS
if os.name == 'nt':
    app.conf.worker_pool = 'solo'