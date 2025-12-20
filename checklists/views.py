# checklists/views.py

import io
import json
from django.views.generic import ListView, View
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML
from django.db import transaction

# Model Imports
from scanner.models import ScanResult  
from .models import ChecklistSubmission, ChecklistResponse, EvidenceFile, ChecklistTemplate

# --- 1. CORE WIZARD VIEWS ---

class ChecklistWizardView(ListView):
    """
    Main interface for performing the manual review.
    Uses 'scan_id' (string) to manage the audit workflow.
    """
    template_name = 'checklists/wizard.html'
    context_object_name = 'responses'

    def dispatch(self, request, *args, **kwargs):
        scan_id_str = self.kwargs.get('scan_id')
        submission = ChecklistSubmission.objects.filter(scan__scan_id=scan_id_str).first()
        
        # If audit is already locked, prevent editing and send to report
        if submission and submission.is_locked:
            messages.info(request, "This audit is locked and can no longer be edited.")
            return redirect('checklists:compliance_report', scan_id=scan_id_str)
            
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        scan_id_str = self.kwargs.get('scan_id')
        scan_obj = get_object_or_404(ScanResult, scan_id=scan_id_str)
        

        # 1. Check if submission exists first to avoid unnecessary transaction noise
        submission = ChecklistSubmission.objects.filter(scan=scan_obj).first()

        # 2. If it doesn't exist, create it and its associated responses atomically
        if not submission:
            with transaction.atomic():
                submission = ChecklistSubmission.objects.create(
                    scan=scan_obj,
                    firm=self.request.user.firm
                )
                
                templates = ChecklistTemplate.objects.filter(active=True)
                responses = [
                    ChecklistResponse(
                        submission=submission,
                        template=t,
                        status='pending'
                    ) for t in templates
                ]
                ChecklistResponse.objects.bulk_create(responses)

        # 3. Return the optimized queryset
        # select_related('template') joins the question data
        # prefetch_related('evidence_files') gets all uploads in one efficient query
        return submission.responses.select_related('template')\
                                   .prefetch_related('evidence_files')\
                                   .order_by('template__code')
                                   
                                   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use the already fetched queryset from the context to avoid re-querying
        responses = context['responses']
        total_count = len(responses)
        completed_count = sum(1 for r in responses if r.status != 'pending')
        
        context.update({
            'submission': get_object_or_404(ChecklistSubmission, scan__scan_id=self.kwargs.get('scan_id')),
            'completion_percentage': int((completed_count / total_count) * 100) if total_count > 0 else 0,
            'completed_count': completed_count,
            'total_count': total_count,
        })
        return context


class UpdateResponseView(View):
    """
    HTMX-driven view to update individual checklist answers.
    """
    def post(self, request, response_id):
        resp = get_object_or_404(ChecklistResponse, id=response_id)
        
        if resp.submission.is_locked:
            return HttpResponseForbidden("Cannot update a locked audit.")

        # Update fields if present in POST data
        if 'status' in request.POST:
            resp.status = request.POST.get('status')
        if 'comment' in request.POST:
            resp.comment = request.POST.get('comment')
        resp.save()
        
        submission = resp.submission
        total = submission.responses.count()
        completed = submission.responses.exclude(status='pending').count()
        
        # Prepare HTMX Response
        django_response = render(request, 'checklists/partials/status_buttons.html', {'resp': resp})
        
        triggers = {
            "responseUpdated": True, 
            "refreshScore": True     
        }
        
        # Signal the UI if the entire audit is ready for completion
        if total > 0 and completed == total:
            triggers["auditComplete"] = True  
            
        django_response["HX-Trigger"] = json.dumps(triggers)
        return django_response 


# --- 2. REPORTING & DASHBOARD VIEWS ---

def compliance_report(request, scan_id):
    """ 
    The 'Gap Analysis' view. Shows compliance scores and risks.
    """
    scan = get_object_or_404(ScanResult, scan_id=scan_id)
    
    # Ensure a submission exists (Saas-safe: creates if missing)
    submission, _ = ChecklistSubmission.objects.get_or_create(
        scan=scan,
        defaults={'firm': scan.firm}
    )

    # Pre-fetch to avoid N+1 issues in the gap analysis table
    
    responses = submission.responses.select_related('template', 'submission__firm').all().order_by('-template__risk_impact')

    # UI Styling Configuration Object
    risk_config = [
        {'level': 'HIGH', 'color': 'rose', 'icon': 'exclamation-circle'},
        {'level': 'MEDIUM', 'color': 'amber', 'icon': 'information-circle'},
        {'level': 'LOW', 'color': 'emerald', 'icon': 'check-circle'},
    ]

    context = {
        'submission': submission,
        'overall_score': submission.calculate_compliance_score() or 0,
        'risk_stats': submission.get_risk_breakdown(), # Method should be in models.py
        'responses': responses,
        'risk_config': risk_config, 
    }
    return render(request, 'checklists/compliance_dashboard.html', context)


def complete_audit(request, submission_id):
    """
    Locks the submission so no further changes can be made.
    """
    submission = get_object_or_404(ChecklistSubmission, id=submission_id, firm=request.user.firm)
    
    if request.method == "POST":
        submission.is_locked = True
        submission.save()
        messages.success(request, "Audit finalized and locked successfully.")
        return redirect('checklists:compliance_report', scan_id=submission.scan.scan_id)
    
    return redirect('checklists:wizard', scan_id=submission.scan.scan_id)


# --- 3. UTILITY & AJAX VIEWS ---

def get_progress(request, submission_id):
    """ Returns a partial HTML for the progress bar. """
    # Added select_related to make the lookup more efficient
    submission = get_object_or_404(ChecklistSubmission.objects.select_related('scan'), id=submission_id)
    responses = submission.responses.all()
    total = responses.count()
    completed = responses.exclude(status='pending').count()
    
    return render(request, 'checklists/partials/progress_bar.html', {
        'submission': submission,  # <--- EXACT LINE TO ADD
        'completion_percentage': int((completed / total) * 100) if total > 0 else 0,
        'completed_count': completed,
        'total_count': total,
    })


class EvidenceUploadView(View):
    """ Handles file uploads for compliance evidence. """
    def post(self, request, response_id):
        response = get_object_or_404(ChecklistResponse, id=response_id)
        if response.submission.is_locked: 
            return HttpResponseForbidden("Audit is locked.")

        files = request.FILES.getlist('evidence')
        for f in files:
            EvidenceFile.objects.create(
                response=response, 
                file=f, 
                filename=f.name, 
                uploaded_by=request.user
            )
        return render(request, 'checklists/partials/evidence_list.html', {'response': response})


def delete_submission(request, submission_id):
    """ Archival view for deleting audit records. """
    if request.method == 'POST':
        submission = get_object_or_404(
            ChecklistSubmission, 
            id=submission_id, 
            firm=request.user.firm
        )
        submission.delete()
        messages.success(request, "Audit record successfully archived.")
    return redirect('checklists:submission_list')


def generate_checklist_pdf(request, pk):
    """ Generates a PDF roadmap using WeasyPrint. """
    submission = get_object_or_404(ChecklistSubmission, id=pk, firm=request.user.firm)
    responses = submission.responses.all().select_related('template')

    context = {
        'submission': submission,
        'responses': responses,
        'firm': request.user.firm,
        'generated_at': timezone.now(),
    }

    html_string = render_to_string('checklists/pdf_roadmap_template.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    
    pdf_buffer = io.BytesIO()
    html.write_pdf(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Compliance_Report_{submission.scan.scan_id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def submission_list(request):
    """ Overview of all audits within the firm. """
    submissions = ChecklistSubmission.objects.filter(
        firm=request.user.firm
    ).select_related('scan').order_by('-created_at')
    
    return render(request, 'checklists/submission_list.html', {'submissions': submissions})
    
    


def get_roadmap(request, scan_id):
    # Fetch the submission and its related scan
    submission = get_object_or_404(
        ChecklistSubmission.objects.select_related('scan'), 
        scan__scan_id=scan_id, 
        firm=request.user.firm
    )
    
    # Get all responses for stats calculation
    all_responses = submission.responses.select_related('template')
    
    # Calculate stats (Fixes the VariableDoesNotExist errors)
    total_count = all_responses.count()
    completed_count = all_responses.exclude(status='pending').count()
    completion_percentage = int((completed_count / total_count) * 100) if total_count > 0 else 0
    
    # Filter for the roadmap (items requiring action)
    # Prefetch evidence_files to avoid N+1 queries in the loop
    roadmap_responses = all_responses.exclude(status='yes').prefetch_related('evidence_files').order_by('template__code')

    context = {
        'submission': submission,
        'responses': roadmap_responses,
        'overall_score': submission.calculate_compliance_score(),
        'last_scan': submission.scan,           # FIX 1
        'completion_percentage': completion_percentage, # FIX 2
        'total_count': total_count,             # FIX 3
        'completed_count': completed_count,     # FIX 4
    }
    return render(request, 'checklists/risk_roadmap.html', context)

def delete_evidence(request, evidence_id):
    """
    Deletes an evidence file. Used via HTMX/AJAX in the wizard.
    """
    evidence = get_object_or_404(EvidenceFile, id=evidence_id)
    
    # Security: Ensure audit isn't locked and user belongs to the right firm
    if evidence.response.submission.is_locked:
        return HttpResponseForbidden("Cannot delete evidence from a locked audit.")
    
    if evidence.response.submission.firm != request.user.firm:
        return HttpResponseForbidden("Unauthorized.")

    evidence.delete()
    return HttpResponse("") # Return empty string for HTMX to remove the element