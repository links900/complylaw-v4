# checklists/urls.py

from django.urls import path
from . import views

app_name = 'checklists'

urlpatterns = [
    # --- Main Entry Points (Using the Scan ID string from the Scanner app) ---
    path('wizard/<str:scan_id>/', views.ChecklistWizardView.as_view(), name='wizard'),
    path('report/<str:scan_id>/', views.compliance_report, name='compliance_report'),
    path('roadmap/<str:scan_id>/', views.get_roadmap, name='roadmap'),
    
    # --- Management Views ---
    path('audits/', views.submission_list, name='submission_list'),
    path('audits/delete/<uuid:submission_id>/', views.delete_submission, name='delete_submission'),
    


    # --- HTMX Wizard Update Endpoints (Using Response/Evidence IDs) ---
    path('update-response/<int:response_id>/', views.UpdateResponseView.as_view(), name='update_response'),
    path('upload-evidence/<int:response_id>/', views.EvidenceUploadView.as_view(), name='upload_evidence'),
    path('delete-evidence/<int:evidence_id>/', views.delete_evidence, name='delete_evidence'),
    
    # --- Submission Specific Actions (Using the Submission UUID) ---
    # Note: We use <uuid:submission_id> because your ChecklistSubmission ID is a UUID
    path('progress/<uuid:submission_id>/', views.get_progress, name='get_progress'),
    path('complete/<uuid:submission_id>/', views.complete_audit, name='complete_audit'),
    path('generate-pdf/<uuid:pk>/', views.generate_checklist_pdf, name='generate_checklist_pdf'),
]