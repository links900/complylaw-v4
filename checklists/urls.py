# checklists/urls.py

from django.urls import path
from . import views

app_name = 'checklists'

urlpatterns = [
    # Change scan_id to uuid if it's also a UUID, 
    # but specifically change submission_id to uuid based on the error:
    path('wizard/<int:scan_id>/', views.ChecklistWizardView.as_view(), name='wizard'),
    
    path('update-response/<int:response_id>/', views.UpdateResponseView.as_view(), name='update_response'),
    
    # FIX: Change <int:submission_id> to <uuid:submission_id>
    path('get-progress/<uuid:submission_id>/', views.get_progress, name='get_progress'),
    path('complete/<uuid:submission_id>/', views.complete_audit, name='complete_audit'),
    
    path('roadmap/<uuid:pk>/', views.get_roadmap, name='get_roadmap'),
    path('generate-pdf/<int:pk>/', views.generate_checklist_pdf, name='generate_checklist_pdf'),

    
    path('upload-evidence/<int:response_id>/', views.EvidenceUploadView.as_view(), name='upload_evidence'),
    path('delete-evidence/<int:evidence_id>/', views.delete_evidence, name='delete_evidence'),
]