# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'


urlpatterns = [
    path('', views.DashboardHomeView.as_view(), name='home'),
    path('alerts/', views.AlertListView.as_view(), name='alerts'),
    path('alert/<int:pk>/read/', views.MarkAlertReadView.as_view(), name='mark_alert_read'),
    
]