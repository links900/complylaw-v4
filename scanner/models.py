# scanner/models.py

from django.db import models
from users.models import FirmProfile
from encrypted_model_fields.fields import EncryptedTextField
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings
import json
import uuid


class ScanResult(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "PENDING"),
        ("RUNNING", "RUNNING"),
        ("COMPLETED", "COMPLETED"),
        ("FAILED", "FAILED"),
        ("CANCELLED", "CANCELLED"),
    ]

    firm = models.ForeignKey(FirmProfile, on_delete=models.CASCADE, related_name="scans")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="scans",
        null=True, # Allows existing scans to remain
        blank=True
    )
    domain = models.CharField(max_length=255)
    scan_date = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def audit_record(self):
        try:
            return self.manual_audit
        except Exception:
            return None

    # Progress
    current_step = models.CharField(max_length=200, blank=True, default="")
    progress = models.IntegerField(default=0)  # 0–100

    # Encrypted raw outputs
    _raw_data = EncryptedTextField(default="{}")
    _breach_alerts = EncryptedTextField(default="{}")
    _checklist_status = EncryptedTextField(default="{}")

    # Computed results
    risk_score = models.FloatField(null=True, blank=True)
    grade = models.CharField(max_length=1, null=True, blank=True)
    recommendations = models.JSONField(default=list)
    anomaly_score = models.FloatField(null=True, blank=True)

    scan_log = EncryptedTextField(blank=True)
    pdf_report_path = models.CharField(max_length=500, null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    # Public scan tracking ID
    scan_id = models.CharField(
        max_length=36, unique=True, default=uuid.uuid4, editable=False
    )

    class Meta:
        indexes = [
            models.Index(fields=["firm", "scan_date"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-scan_date"]

    def __str__(self):
        return f"Scan {self.pk} – {self.domain} – {self.status}"

    # ---------------------------------------------------------------- #
    # JSON helpers
    # ---------------------------------------------------------------- #
    def _get_json(self, field):
        return json.loads(field) if field else {}

    def _set_json(self, field_name, value):
        setattr(self, field_name, json.dumps(value, cls=DjangoJSONEncoder))

    # Raw data
    def get_raw_data(self):
        return self._get_json(self._raw_data)

    def set_raw_data(self, value):
        self._set_json("_raw_data", value)

    raw_data = property(get_raw_data, set_raw_data)

    # Breach alerts
    def get_breach_alerts(self):
        return self._get_json(self._breach_alerts)

    def set_breach_alerts(self, value):
        self._set_json("_breach_alerts", value)

    breach_alerts = property(get_breach_alerts, set_breach_alerts)

    # Checklist results
    def get_checklist_status(self):
        return self._get_json(self._checklist_status)

    def set_checklist_status(self, value):
        self._set_json("_checklist_status", value)

    checklist_status = property(get_checklist_status, set_checklist_status)

    # ---------------------------------------------------------------- #
    # PDF-safe getters
    # ---------------------------------------------------------------- #
    def get_findings(self):
        return self.raw_data.get("findings", [])

    def get_recommendations(self):
        if isinstance(self.recommendations, list):
            return self.recommendations
        return self.raw_data.get("recommendations", [])

    def get_vulnerabilities(self):
        return self.raw_data.get("vulnerabilities", [])

    def get_scanned_urls(self):
        return self.raw_data.get("scanned_urls", [])

    # ---------------------------------------------------------------- #
    # Duration
    # ---------------------------------------------------------------- #
    @property
    def scan_duration(self):
        if self.completed_at:
            delta = self.completed_at - self.scan_date
            mins, secs = divmod(delta.seconds, 60)
            return f"{mins}m {secs}s"
        return "—"


# ---------------------------------------------------------------------- #
# SIGNAL — Generate ComplianceReport When Scan Completes
# ---------------------------------------------------------------------- #
@receiver(post_save, sender=ScanResult)
def create_compliance_report(sender, instance, created, **kwargs):

    if instance.status != "COMPLETED":
        return

    from reports.models import ComplianceReport

    report, created_report = ComplianceReport.objects.get_or_create(scan=instance)

    # Copy findings if needed
    findings = instance.raw_data.get("findings", [])
    if findings and (created_report or not report.findings):
        report.findings = findings
        report.save()

    # Generate PDF if missing
    if not report.pdf_file:
        report.generate_pdf(request=None)
