# scanner/urls.py


from django.urls import path
from . import views

app_name = 'scanner'

urlpatterns = [
    # Dashboard (root)
    path('', views.ScanDashboardView.as_view(), name='dashboard'),

    # Scan List
    path('list/', views.ScanListView.as_view(), name='scan_list'),

    # Start Scan
    path('run/', views.StartScanView.as_view(), name='run_scan'),
    path('run/modal/', views.RunScanModalView.as_view(), name='run_modal'),

    # --- ALL SCAN DETAILS AND ACTIONS UPDATED TO STRING-BASED ID ---
    
    # Details & Progress
    path('scan/<str:scan_id>/', views.scan_status, name='scan_status'),
    path('scan/<str:scan_id>/partial/', views.scan_status_partial, name='scan_status_partial'),

    # PDF Generation
    path('scan/<str:scan_id>/pdf/', views.generate_pdf, name='pdf'),

    # Actions
    path('scan/<str:scan_id>/cancel/', views.CancelScanView.as_view(), name='cancel'),
    path('scan/<str:scan_id>/retry/', views.RetryScanView.as_view(), name='retry'),
    
    # Modals
    path('scan/<str:scan_id>/checklist-modal/', views.checklist_modal_view, name='checklist_modal'),
]