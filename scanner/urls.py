# scanner/urls.py
from django.urls import path
from . import views

app_name = 'scanner'

urlpatterns = [
    # Dashboard (root)
    path('', views.ScanDashboardView.as_view(), name='dashboard'),

    # Scan List
    path('list/', views.ScanListView.as_view(), name='scan_list'),

    # Start Scan – POST (function)
    path('run/', views.StartScanView.as_view(), name='run_scan'),

    # GET: HTMX modal
    path('run/modal/', views.RunScanModalView.as_view(), name='run_modal'),

    # Scan Details + HTMX Partial
    path('scan/<int:pk>/', views.ScanStatusView.as_view(), name='scan_status'),
    path('scan/<int:pk>/partial/', views.scan_status_partial, name='scan_status_partial'),

    # PDF Generation
    path('scan/<int:pk>/pdf/', views.generate_pdf, name='pdf'),

    # Actions
    path('scan/<int:pk>/cancel/', views.CancelScanView.as_view(), name='cancel'),
    path('scan/<int:pk>/retry/', views.RetryScanView.as_view(), name='retry'),
]