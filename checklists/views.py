#checklists\views.py

from django.views.generic import ListView, View
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseForbidden
from .models import ChecklistSubmission, ChecklistResponse, EvidenceFile
from django.shortcuts import redirect
from django.contrib import messages
from django.template.loader import render_to_string
from weasyprint import HTML
import io





class ChecklistWizardView(ListView):
    template_name = 'checklists/wizard.html'
    context_object_name = 'responses'

    def get_queryset(self):
        scan_id = self.kwargs.get('scan_id')
        submission, created = ChecklistSubmission.objects.get_or_create(
            scan_id=scan_id,
            defaults={'firm': self.request.user.firm}
        )

        if created:
            from .models import ChecklistTemplate, ChecklistResponse
            templates = ChecklistTemplate.objects.filter(active=True)
            for t in templates:
                ChecklistResponse.objects.get_or_create(
                    submission=submission,
                    template=t,
                    defaults={'status': 'pending'}
                )

        return submission.responses.select_related('template').order_by('template__code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = ChecklistSubmission.objects.get(scan_id=self.kwargs.get('scan_id'))
        
        # --- NEW LOGIC: Calculate initial progress for the template ---
        responses = submission.responses.all()
        total_count = responses.count()
        completed_count = responses.exclude(status='pending').count()
        percentage = int((completed_count / total_count) * 100) if total_count > 0 else 0
        
        context['submission'] = submission
        context['completion_percentage'] = percentage
        context['completed_count'] = completed_count
        context['total_count'] = total_count
        # -------------------------------------------------------------
        return context



class UpdateResponseView(View):
    def post(self, request, response_id):
        resp = get_object_or_404(ChecklistResponse, id=response_id)
        
        if 'status' in request.POST:
            resp.status = request.POST.get('status')
        if 'comment' in request.POST:
            resp.comment = request.POST.get('comment')
            
        resp.save()
        
        # Return the buttons partial so the clicked button turns blue
        django_response = render(request, 'checklists/partials/status_buttons.html', {'resp': resp})
        
        # Trigger the progress bar update
        django_response["HX-Trigger"] = "responseUpdated"
        
        return django_response

class EvidenceUploadView(View):
    def post(self, request, response_id):
        response = get_object_or_404(ChecklistResponse, id=response_id)
        if response.submission.is_locked: return HttpResponseForbidden()

        files = request.FILES.getlist('evidence')
        for f in files:
            EvidenceFile.objects.create(
                response=response, file=f, filename=f.name, uploaded_by=request.user
            )
        return render(request, 'checklists/partials/evidence_list.html', {'response': response})



def delete_evidence(request, evidence_id):
    evidence = get_object_or_404(EvidenceFile, id=evidence_id)
    # Security: check if audit is locked
    if evidence.response.submission.is_locked:
        return HttpResponseForbidden()
        
    evidence.delete()
    return HttpResponse("") # Returns empty string so HTMX removes the element
    

def get_progress(request, submission_id):
    submission = get_object_or_404(ChecklistSubmission, id=submission_id)
    # This counts all responses generated for this specific audit
    responses = submission.responses.all()
    
    total_count = responses.count()
    # Count only those that are 'yes', 'no', or 'partial' (not 'pending')
    completed_count = responses.exclude(status='pending').count()
    
    # Avoid division by zero error
    percentage = int((completed_count / total_count) * 100) if total_count > 0 else 0
    
    return render(request, 'checklists/partials/progress_bar.html', {
        'completion_percentage': percentage,
        'completed_count': completed_count,
        'total_count': total_count,
    })
    



def complete_audit(request, submission_id):
    submission = get_object_or_404(ChecklistSubmission, id=submission_id)
    
    if request.method == "POST":
        submission.is_locked = True
        submission.status = 'completed'
        submission.save()
        
        messages.success(request, "Audit completed successfully! Your report is being generated.")
        return redirect('reports:report_detail', scan_id=submission.scan_id)
    
    return redirect('checklists:wizard', scan_id=submission.scan_id)
    
    


def get_roadmap(request, submission_id):
    submission = get_object_or_404(ChecklistSubmission, id=submission_id)
    responses = submission.responses.all()
    total = responses.count()
    completed = responses.exclude(status='pending').count()
    
    context = {
        'submission': submission,
        'total_count': total,
        'completed_count': completed,
        'completion_percentage': int((completed / total) * 100) if total > 0 else 0,
    }
    return render(request, 'checklists/risk_roadmap.html', context)
    
    

def generate_checklist_pdf(request, pk):
    # Fetch the manual audit submission
    submission = get_object_or_404(ChecklistSubmission, id=pk, firm=request.user.firm)
    
    # Get all responses for this submission
    responses = submission.responses.all().select_related('question')

    context = {
        'submission': submission,
        'responses': responses,
        'firm': request.user.firm,
        'generated_at': now(),
    }

    # 1. Render to HTML string
    html_string = render_to_string('checklists/pdf_roadmap_template.html', context)
    
    # 2. Generate PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf_buffer = io.BytesIO()
    html.write_pdf(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()

    # 3. Return as Download
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Roadmap_{request.user.firm.firm_name}_{submission.id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response