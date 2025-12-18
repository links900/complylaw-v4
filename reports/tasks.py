#reports\tasks.py

import os
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from scanner.models import ScanResult # FIXED
from checklists.services import ScoringService
from checklists.models import ChecklistSubmission

@shared_task(name="generate_unified_report")
def generate_unified_report(scan_id):
    scan = ScanResult.objects.get(id=scan_id) # FIXED
    submission = ChecklistSubmission.objects.get(scan=scan)
    
    submission.is_locked = True
    submission.save()

    scores = ScoringService.calculate(submission.id)
    
    context = {
        'scan': scan,
        'submission': submission,
        'responses': submission.responses.select_related('template').prefetch_related('evidence_files').all(),
        'scores': scores,
        'generated_at': timezone.now(),
        'base_url': settings.SITE_URL
    }

    html_string = render_to_string('reports/pdf_template_enterprise.html', context)
    report_filename = f"Compliance_Report_{scan.domain}_{str(scan.id)[:8]}.pdf"
    report_path = os.path.join(settings.MEDIA_ROOT, 'reports', 'pdfs', report_filename)
    
    HTML(string=html_string, base_url=settings.STATIC_ROOT).write_pdf(report_path)

    # Update ScanResult with the report URL
    scan.report_url = os.path.join(settings.MEDIA_URL, 'reports/pdfs/', report_filename)
    scan.status = 'COMPLETED'
    scan.save()

    return report_path