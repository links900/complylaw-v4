#checklists\models.py


import uuid
from django.db import models
from django.conf import settings
from scanner.models import ScanResult
from dashboard.models import FirmProfile

class RiskImpact(models.TextChoices):
    HIGH = 'HIGH', 'High'
    MEDIUM = 'MEDIUM', 'Medium'
    LOW = 'LOW', 'Low'

class ChecklistTemplate(models.Model):
    standard = models.CharField(max_length=50, db_index=True)
    code = models.CharField(max_length=50)
    reference_article = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    risk_impact = models.CharField(max_length=10, choices=RiskImpact.choices, default=RiskImpact.MEDIUM)
    weight = models.FloatField(default=1.0)
    requires_evidence = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('standard', 'code')

    def __str__(self):
        return f"[{self.standard}] {self.code}"

class ChecklistSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.OneToOneField(ScanResult, on_delete=models.CASCADE, related_name='manual_audit')
    firm = models.ForeignKey(FirmProfile, on_delete=models.CASCADE)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ChecklistResponse(models.Model):
    STATUS_CHOICES = [("yes", "Yes"), ("no", "No"), ("partial", "Partial"), ("na", "N/A")]
    submission = models.ForeignKey(ChecklistSubmission, on_delete=models.CASCADE, related_name='responses')
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="no")
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('submission', 'template')

class EvidenceFile(models.Model):
    response = models.ForeignKey(ChecklistResponse, on_delete=models.CASCADE, related_name='evidence_files')
    file = models.FileField(upload_to="evidence/%Y/%m/%d/")
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)