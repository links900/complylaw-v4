# scanner/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Live scan progress
    re_path(r'ws/scan/(?P<scan_id>[\w-]+)/$', consumers.ScanProgressConsumer.as_asgi()),
    

    # Live notifications
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
