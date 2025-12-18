# reports/models.py

import os
import json
from django.db import models
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from encrypted_model_fields.fields import EncryptedTextField
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings


class ComplianceReport(models.Model):
    """
    One-to-one encrypted compliance report generated after a ScanResult completes.
    """
    scan = models.OneToOneField(
        "scanner.ScanResult",
        on_delete=models.CASCADE,
        related_name="compliance_report"
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    # Encrypted JSON list of findings
    _findings = EncryptedTextField(default="[]")

    # PDF file stored in MEDIA_ROOT/reports/pdfs/
    pdf_file = models.FileField(upload_to='reports/pdfs/', null=True, blank=True)

    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Compliance Report"
        verbose_name_plural = "Compliance Reports"

    def __str__(self):
        return f"Report #{self.pk} — {self.scan.domain} — {self.generated_at.date()}"

    # ------------------------------------------------------------------ #
    # JSON property wrapper for encrypted findings
    # ------------------------------------------------------------------ #
    def get_findings(self):
        if not self._findings:
            return []
        try:
            return json.loads(self._findings)
        except json.JSONDecodeError:
            return []

    def set_findings(self, value):
        self._findings = json.dumps(value, cls=DjangoJSONEncoder)

    findings = property(get_findings, set_findings)

    # ------------------------------------------------------------------ #
    # PDF generator
    # ------------------------------------------------------------------ #
    def generate_pdf(self, request=None):
        """
        Generate PDF using reports/pdf_template.html and store into pdf_file.
        """
        html_string = render_to_string('reports/pdf_template.html', {
            'report': self,
            'scan': self.scan,
            'firm': self.scan.firm,
            'generated_at': timezone.now(),
            'findings': self.findings,
            'recommendations': self.scan.raw_data.get('recommendations', []),
            'scan_duration': self.scan.scan_duration,
            'request': request,  # Can be None
        })

        base_url = request.build_absolute_uri('/') if request else settings.MEDIA_ROOT

        pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf()

        filename = f"report_{self.pk}_{self.scan.domain}.pdf"
        self.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)


# ---------------------------------------------------------------------- #
# SIGNAL: Auto-create ComplianceReport when ScanResult is complete
# ---------------------------------------------------------------------- #
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender="scanner.ScanResult")
def create_compliance_report(sender, instance, created, **kwargs):
    """
    Runs whenever a ScanResult is saved.
    If its status becomes 'complete', generate a compliance report and PDF.
    """

    if instance.status != "complete":
        return

    # Local import → prevents circular import
    from reports.models import ComplianceReport

    report, created_report = ComplianceReport.objects.get_or_create(scan=instance)

    # Copy findings from ScanResult.raw_data
    if created_report or not report.findings:
        findings = instance.raw_data.get('findings', [])
        report.findings = findings
        report.save(update_fields=['_findings'])

    # Generate PDF only if missing
    if not report.pdf_file:
        report.generate_pdf()
