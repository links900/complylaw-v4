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
from django.conf import settings
from django.utils.timezone import now
from django.core.files.base import ContentFile
import json
import uuid
import re
import io
from weasyprint import HTML

from core.mixins import FirmRequiredMixin
from .models import ScanResult
from .tasks import run_compliance_scan
from reports.models import ComplianceReport, ReportVerification
from reports.utils import calculate_sha256_bytes

# Alias for convenience if needed by legacy code
Scan = ScanResult

# === HELPER / UTILITY VIEWS ===

def checklist_modal_view(request, scan_id):
    scan = get_object_or_404(ScanResult, scan_id=scan_id, firm=request.user.firm)
    return render(request, 'scanner/partials/checklist_prompt.html', {
        'scan': scan,
        'debug_mode': False
    })

def keep_alive(request):
    return HttpResponse("OK")

# === DASHBOARD ===
class ScanDashboardView(LoginRequiredMixin, ListView):
    model = ScanResult
    template_name = 'scanner/dashboard.html'
    context_object_name = 'scans'
    
    def get_queryset(self):
        #return ScanResult.objects.filter(
        #    firm=self.request.user.firm
        #).select_related('firm').order_by('-scan_date')
        return ScanResult.objects.filter(
            firm=self.request.user.firm
             ).select_related('firm', 'manual_audit').order_by('-scan_date')
        
        

# === SCAN LIST ===
class ScanListView(FirmRequiredMixin, ListView):
    model = ScanResult
    template_name = 'scanner/scan_list.html'
    context_object_name = 'scans'

    def get_queryset(self):
        return ScanResult.objects.filter(firm=self.request.user.firm).order_by('-scan_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        latest_scan = qs.first()
        context['latest_scan_obj'] = latest_scan
        context['latest_grade'] = latest_scan.grade if latest_scan else None
        context['total_scans'] = qs.count()
        return context

# === RUN SCAN MODAL (HTMX) ===
class RunScanModalView(LoginRequiredMixin, TemplateView):
    template_name = 'scanner/partials/run_scan_modal.html'

    def get(self, request, *args, **kwargs):
        if request.htmx:
            return super().get(request, *args, **kwargs)
        return redirect('scanner:scan_list')

# === START SCAN ===
@method_decorator(ratelimit(key='user', rate='20/h', method='POST', block=True), name='dispatch')
class StartScanView(LoginRequiredMixin, View):
    def post(self, request):
        domain = request.POST.get('domain', '').strip().lower()
        if not domain:
            messages.error(request, "Please enter a domain.")
            return redirect('scanner:scan_list')

        if not re.match(r'^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$', domain):
            messages.error(request, "Invalid domain format.")
            return redirect('scanner:scan_list')

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
        
        run_compliance_scan.delay(scan.pk)
        messages.success(request, f"Scan started for {domain}", extra_tags="scan_started")
        
        if request.htmx:
            return HttpResponseLocation(reverse('scanner:scan_status', args=[scan.scan_id]))
        return redirect('scanner:dashboard')

# === SCAN STATUS ===

# We define this as a function to match your urls.py 'views.scan_status'
def scan_status(request, scan_id):
    scan = get_object_or_404(ScanResult, scan_id=scan_id, firm=request.user.firm)
    context = {
        'scan': scan,
        'active_statuses': ("RUNNING", "PENDING")
    }
    return render(request, 'scanner/scan_status.html', context)

# === HTMX PARTIAL: Progress Update ===
def scan_status_partial(request, scan_id):
    scan = get_object_or_404(ScanResult, scan_id=scan_id, firm=request.user.firm)
    context = {
        'scan': scan,
        'active_statuses': ('RUNNING', 'PENDING'),
    }
    
    html = render_to_string('scanner/partials/scan_progress.html', context, request=request)
    
    if scan.status == 'COMPLETED':
        user_firm = request.user.firm
        user_tier = getattr(user_firm, 'subscription_tier', '').upper()
        if user_tier in ['PRO', 'ENTERPRISE']:
            html += render_to_string('scanner/partials/checklist_prompt.html', {'scan': scan}, request=request)
    
    return HttpResponse(html)

# === CANCEL SCAN ===
class CancelScanView(LoginRequiredMixin, View):
    def post(self, request, scan_id):
        scan = get_object_or_404(ScanResult, scan_id=scan_id, firm=request.user.firm)
        if scan.status in ['PENDING', 'RUNNING']:
            scan.status = 'CANCELLED'
            scan.scan_log = (scan.scan_log or "") + '\n[Cancelled by user]'
            scan.save()
        return HttpResponseClientRefresh()

# === RETRY SCAN ===
class RetryScanView(LoginRequiredMixin, View):
    def post(self, request, scan_id):
        old_scan = get_object_or_404(ScanResult, scan_id=scan_id, firm=request.user.firm)
        if old_scan.status != 'FAILED':
            return JsonResponse({'error': 'Only FAILED scans can be retried'}, status=400)

        new_scan = ScanResult.objects.create(
            firm=old_scan.firm,
            domain=old_scan.domain,
            status='PENDING',
            scan_id=str(uuid.uuid4())[:8],
            scan_log='Retrying FAILED scan...'
        )
        run_compliance_scan.delay(new_scan.pk)
        return HttpResponseLocation(reverse('scanner:scan_status', args=[new_scan.scan_id]))

# === GENERATE PDF ===
def generate_pdf(request, scan_id):
    scan = get_object_or_404(ScanResult, scan_id=scan_id, firm=request.user.firm)

    raw_findings = scan.get_findings() or []
    findings_list = []
    for f in raw_findings:
        if isinstance(f, str):
            findings_list.append({
                'standard': '—', 'title': f, 'risk_level': '—', 'details': f, 'module': 'General'
            })
        elif isinstance(f, dict):
            findings_list.append({
                'standard': f.get('standard') or '—',
                'title': f.get('title') or '—',
                'risk_level': f.get('risk_level') or '—',
                'details': f.get('details') or '—',
                'module': f.get('module') or 'General'
            })

    raw_recommendations = scan.get_recommendations() if hasattr(scan, 'get_recommendations') else []
    normalized_rec = []
    for r in raw_recommendations:
        if isinstance(r, dict):
            normalized_rec.append({
                'title': r.get('title', '—'),
                'description': r.get('description') or r.get('details') or '—',
                'priority': r.get('priority', '—'),
            })
        else:
            normalized_rec.append({'title': str(r), 'description': '—', 'priority': '—'})

    current_host = request.get_host() if request else getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
    context = {
        'scan': scan,
        'findings': findings_list,
        'recommendations': normalized_rec,
        'host': current_host,
    }

    html_string = render_to_string('reports/pdf_template.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))

    pdf_buffer = io.BytesIO()
    html.write_pdf(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()

    pdf_hash = calculate_sha256_bytes(pdf_bytes)
    pdf_filename = f"Compliance_Report_{scan.domain}_{scan.scan_id}.pdf"

    report, _ = ComplianceReport.objects.get_or_create(
        scan=scan,
        defaults={'generated_at': now()}
    )
    report.pdf_file.save(pdf_filename, ContentFile(pdf_bytes), save=True)

    ReportVerification.objects.update_or_create(
        report_id=scan.scan_id,
        defaults={
            'domain': scan.domain,
            'scan': scan,
            'generated_at': now(),
            'pdf_sha256': pdf_hash,
        }
    )

    report.pdf_file.open('rb')
    response = HttpResponse(report.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
    return response

def rate_limit_exceeded_view(request, exception=None):
    return HttpResponse("You have exceeded the request limit. Please try again later.", status=429)