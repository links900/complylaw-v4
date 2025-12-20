# checklists/urls.py

from django.urls import path
from . import views

app_name = 'checklists'

urlpatterns = [
    # The main entry point from a scan
    path('wizard/<int:scan_id>/', views.ChecklistWizardView.as_view(), name='wizard'),
    
    path('audits/', views.submission_list, name='submission_list'),
    
    
    # Dashboard/Report View
    path('report/<int:scan_id>/', views.compliance_report, name='compliance_report'),
    
    
    # HTMX endpoints for the wizard
    path('update-response/<int:response_id>/', views.UpdateResponseView.as_view(), name='update_response'),
    path('upload-evidence/<int:response_id>/', views.EvidenceUploadView.as_view(), name='upload_evidence'),
    path('delete-evidence/<int:evidence_id>/', views.delete_evidence, name='delete_evidence'),
    #path('get-progress/<int:submission_id>/', views.get_progress, name='get_progress'),
    
    path('get-progress/<uuid:submission_id>/', views.get_progress, name='get_progress'),
    path('complete/<uuid:submission_id>/', views.complete_audit, name='complete_audit'),
    
    
    path('roadmap/<uuid:pk>/', views.get_roadmap, name='get_roadmap'),
    path('generate-pdf/<int:pk>/', views.generate_checklist_pdf, name='generate_checklist_pdf'),
    
    # Finalization
    path('complete/<int:submission_id>/', views.complete_audit, name='complete_audit'),
]