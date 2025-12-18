# scanner/views.py
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django_htmx.http import HttpResponseLocation, HttpResponseClientRefresh
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.core.cache import cache
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from django.conf import settings
from celery import current_app
import json
import uuid
import re
import io
from weasyprint import HTML
from django.core.files.base import ContentFile
from core.mixins import FirmRequiredMixin
# scanner/views.py
from .models import ScanResult as Scan  # Alias the model name
from .models import ScanResult
from .tasks import run_compliance_scan
from reports.models import ComplianceReport
from reports.models import ReportVerification
from reports.utils import calculate_sha256_bytes
from django.utils.timezone import now




def keep_alive(request):
    return HttpResponse("OK")  # Call this every 10min via cron or external ping
    
    

# === DASHBOARD ===
class ScanDashboardView(LoginRequiredMixin, ListView):
    model = ScanResult
    template_name = 'scanner/dashboard.html'
    context_object_name = 'scans'
    
    def get_queryset(self):
        return ScanResult.objects.filter(
            #firm=self.request.user.firmprofile
            firm=self.request.user.firm
        ).select_related('firm').order_by('-scan_date')


# === SCAN LIST ===
# scanner/views.py

class ScanListView(FirmRequiredMixin, ListView):
    model = ScanResult
    template_name = 'scanner/scan_list.html'
    context_object_name = 'scans'  # This matches your {% for scan in scans %}

    def get_queryset(self):
        # Filter scans by the user's firm and order by date
        return ScanResult.objects.filter(firm=self.request.user.firm).order_by('-scan_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        
        # 1. Get the latest scan object for the "Last Scan" stat card
        latest_scan = qs.first()
        context['latest_scan_obj'] = latest_scan
        
        # 2. Get the grade for the "Latest Grade" stat card
        # Using .grade if it exists, otherwise None (template handles the dash)
        context['latest_grade'] = latest_scan.grade if latest_scan else None
        
        # 3. Get total count
        context['total_scans'] = qs.count()
        
        return context


# === RUN SCAN MODAL (HTMX) ===
class RunScanModalView(LoginRequiredMixin, TemplateView):
    template_name = 'scanner/partials/run_scan_modal.html'

    def get(self, request, *args, **kwargs):
        if request.htmx:
            return super().get(request, *args, **kwargs)
        return redirect('scanner:scan_list')


# === START SCAN (WITH RATE LIMIT) ===
@method_decorator(ratelimit(key='user', rate='20/h', method='POST', block=True), name='dispatch')
class StartScanView(LoginRequiredMixin, View):
    
    def post(self, request):
        
        domain = request.POST.get('domain', '').strip().lower()
        if not domain:
            messages.error(request, "Please enter a domain.")
            return redirect('scanner:run_scan')

        if not re.match(r'^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$', domain):
            messages.error(request, "Invalid domain format.")
            return redirect('scanner:run_scan')

        if ScanResult.objects.filter(
            firm=request.user.firm,
            domain=domain,
            status__in=['PENDING', 'RUNNING']
        ).exists():
            messages.warning(request, f"A scan for {domain} is already in progress.")
            return redirect('scanner:dashboard')
        
        scan = ScanResult.objects.create(
            firm=request.user.firm,
            domain=domain,
            status='PENDING',
            scan_id=str(uuid.uuid4())[:8]
        )
        #print(scan.id)
        #print(scan.status)

        
        run_compliance_scan.delay(scan.pk)
        #messages.success(request, f"Scan started for <strong>{domain}</strong>.")
        messages.success(request, f"Scan started for {domain}", extra_tags="scan_started")
        
        if request.htmx:
            #print("here in htmx")
            return HttpResponseLocation(reverse('scanner:scan_status', args=[scan.id]))
        #print("here after htmx check")
        return redirect('scanner:dashboard')


# === SCAN STATUS (Real-Time via HTMX) ===
class ScanStatusView(LoginRequiredMixin, DetailView):
    model = ScanResult
    template_name = 'scanner/scan_status.html'
    context_object_name = 'scan'
    #print("1>>>>")
    #print(model.id)
    #print(model)

    def get_queryset(self):
        return ScanResult.objects.filter(firm=self.request.user.firm)
        
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_statuses"] = ("RUNNING", "PENDING")
        return context

# === HTMX PARTIAL: Progress Update ===
def scan_status_partial(request, pk):
    scan = get_object_or_404(ScanResult, pk=pk, firm=request.user.firm)
    #print("2>>>>")
    #print(scan.id)
    #print(scan)
    #return render(request, 'scanner/partials/scan_progress.html', {'scan': scan})
    
    
    html = render_to_string('scanner/partials/scan_progress.html', {'scan': scan,'active_statuses': ('RUNNING', 'PENDING'),})
    
    if scan.status == 'COMPLETED':
        html += '<script>htmx.remove(htmx.find("#scan-progress"))</script>'
        messages.success(request, f"Scan completed. ", extra_tags="scan_complete")
        
    
    return HttpResponse(html)


# === CANCEL SCAN ===
class CancelScanView(LoginRequiredMixin, View):
    def post(self, request, pk):
        scan = get_object_or_404(ScanResult, pk=pk, firm=request.user.firm)
        if scan.status in ['PENDING', 'RUNNING']:
            scan.status = 'CANCELLED'
            scan.scan_log += '\n[Cancelled by user]'
            scan.save()
        return HttpResponseClientRefresh()


# === RETRY SCAN ===
class RetryScanView(LoginRequiredMixin, View):
    def post(self, request, pk):
        old_scan = get_object_or_404(ScanResult, pk=pk, firm=request.user.firm)
        if old_scan.status != 'FAILED':
            return JsonResponse({'error': 'Only FAILED scans can be retried'}, status=400)

        new_scan = ScanResult.objects.create(
            firm=old_scan.firm,
            domain=old_scan.domain,
            status='PENDING',
            scan_id=str(uuid.uuid4())[:8],
            scan_log='Retrying FAILED scan...'
        )
        run_compliance_scan.delay(new_scan.id)
        return HttpResponseLocation(reverse('scanner:scan_status', args=[new_scan.id]))


# === GENERATE PDF (WeasyPrint) ===ScanListView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from weasyprint import HTML
import io

def generate_pdf(request, pk):
    scan = get_object_or_404(ScanResult, id=pk, firm=request.user.firm)

    # === Extract findings ===
    raw_findings = scan.get_findings() or []
    
    findings_list = []

    for f in raw_findings:

        # If f is a plain string (older scans), convert it to dict
        if isinstance(f, str):
            findings_list.append({
                'standard': '—',
                'title': f,
                'risk_level': '—',
                'details': f,
                'module': 'General'
            })
            continue

        # If f is not even a dict, skip
        if not isinstance(f, dict):
            continue

        # Normal structured finding
        findings_list.append({
            'standard': f.get('standard') or '—',
            'title': f.get('title') or '—',
            'risk_level': f.get('risk_level') or '—',
            'details': f.get('details') or '—',
            'module': f.get('module') or 'General'
        })

    raw_recommendations = scan.get_recommendations() if hasattr(scan, 'get_recommendations') else []

    normalized_recommendations = []
    for r in raw_recommendations:
        if isinstance(r, dict):
            normalized_recommendations.append({
                'title': r.get('title', '—'),
                'description': r.get('description') or r.get('details') or '—',
                'priority': r.get('priority', '—'),
            })
        else:
            normalized_recommendations.append({
                'title': str(r),
                'description': '—',
                'priority': '—',
            })

    current_host = request.get_host() if request else getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
    context = {
        'scan': scan,
        'findings': findings_list,
        'recommendations': normalized_recommendations,
        'host': current_host,
        
    }


    # Render template
    html_string = render_to_string('reports/pdf_template.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))

    '''
    pdf_file = io.BytesIO()
    html.write_pdf(pdf_file)
    '''
    # Hash creation and store for verification
    pdf_buffer = io.BytesIO()
    html.write_pdf(pdf_buffer)

    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()

    pdf_hash = calculate_sha256_bytes(pdf_bytes)

    # === Save PDF to ComplianceReport for report view download ===
    pdf_filename = f"Compliance_Report_{scan.domain}_{scan.scan_id}.pdf"
    pdf_content = ContentFile(pdf_bytes, name=pdf_filename)

    report, created = ComplianceReport.objects.get_or_create(
        scan=scan,
        defaults={'pdf_file': pdf_content, 'generated_at': now()}
    )
    if not created:
        # Update existing PDF
        report.pdf_file.save(pdf_filename, pdf_content, save=True)

    # === Save verification record for scanner verify page ===
    report_verification, created = ReportVerification.objects.get_or_create(
        report_id=scan.scan_id,  # unique field
        defaults={
            'domain': scan.domain,
            'scan': scan,
            'generated_at': now(),
            'pdf_file': pdf_content,
            'pdf_sha256': pdf_hash,
        }
    )



    # === Serve PDF and return reponse ===

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Compliance_Report_{scan.domain}_{scan.scan_id}.pdf"'
    #response.write(pdf_file.getvalue())
    response.write(pdf_bytes)

    
   # pdf_file.close()

    return response

    
    
    

from django.http import HttpResponse

def rate_limit_exceeded_view(request, exception=None):
    return HttpResponse(
        "You have exceeded the request limit. Please try again later.",
        status=429
    )