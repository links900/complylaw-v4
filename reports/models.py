# reports/models.py

import os
import json
from django.db import models
import uuid
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from encrypted_model_fields.fields import EncryptedTextField
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from django.utils.html import strip_tags

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
        # Ensure serialisable
        self._findings = json.dumps(value, cls=DjangoJSONEncoder)

    findings = property(get_findings, set_findings)

    # ------------------------------------------------------------------ #
    # GDPR mapping helpers and scoring
    # ------------------------------------------------------------------ #
    def map_gdpr_articles(self, findings=None):
        """
        Best-effort mapping of findings to GDPR articles. Adds 'gdpr_article' to each finding dict.
        Returns the updated findings list (does not persist automatically).
        """
        if findings is None:
            findings = self.findings

        # Simple keyword -> GDPR article mapping. Extend as needed.
        gdpr_map = {
            "lawful basis": ["Article 6"],
            "consent": ["Article 6", "Article 7"],
            "data subject": ["Article 12", "Article 15"],
            "access": ["Article 15"],
            "portability": ["Article 20"],
            "erasure": ["Article 17"],
            "right to be forgotten": ["Article 17"],
            "security": ["Article 32"],
            "breach": ["Article 33", "Article 34"],
            "processor": ["Article 28"],
            "processor agreement": ["Article 28"],
            "data protection": ["Article 24", "Article 32"],
            "privacy policy": ["Article 12", "Article 13"],
            "cookie": ["Article 7", "Recital 30"],
            "tracking": ["Article 6", "Recital 30"],
            "consent banner": ["Article 7"],
            "child": ["Article 8"],
            "minimisation": ["Article 5"],
            "retention": ["Article 5"],
            "encryption": ["Article 32"],
            "mfa": ["Article 32"],
            "incident response": ["Article 33"],
            "dsar": ["Article 15", "Article 12"],
            "data subject access": ["Article 15"],
        }

        # Normalize and map
        updated = []
        for f in findings:
            title = (f.get('title') or f.get('description') or "").lower()
            gdpr_articles = set()
            for kw, arts in gdpr_map.items():
                if kw in title:
                    for a in arts:
                        gdpr_articles.add(a)
            if not gdpr_articles:
                # fallback: category based mapping
                cat = (f.get('category') or "").lower()
                if "privacy" in cat or "gdpr" in cat:
                    gdpr_articles.add("Article 12")
                elif "security" in cat or "vulnerab" in cat:
                    gdpr_articles.add("Article 32")

            f['gdpr_article'] = ", ".join(sorted(gdpr_articles)) if gdpr_articles else "—"
            updated.append(f)

        return updated

    def calculate_legal_exposure(self, findings=None):
        """
        Calculate a Legal Exposure Index (0-100).
        Algorithm (explainable):
          - Assign base scores: High=30, Medium=15, Low=5
          - GDPR-related findings get a 1.25 multiplier
          - Add small weight for issue count
          - Normalize to 0-100
        """
        if findings is None:
            findings = self.findings

        severity_weight = {
            "high": 30,
            "critical": 40,
            "medium": 15,
            "moderate": 15,
            "low": 5,
            "informational": 1,
            "info": 1,
        }

        raw_score = 0.0
        for f in findings:
            r = (f.get('risk_level') or f.get('severity') or "medium").lower()
            base = severity_weight.get(r, 15)

            # GDPR relevance
            gdpr_related = False
            if f.get('gdpr_article') and f.get('gdpr_article') != "—":
                gdpr_related = True
            # Also check title/description for gdpr keywords
            t = (f.get('title') or f.get('description') or "").lower()
            if any(k in t for k in ['gdpr', 'consent', 'erasure', 'data subject', 'dsar', 'right to be forgotten', 'data protection']):
                gdpr_related = True

            multiplier = 1.25 if gdpr_related else 1.0

            raw_score += base * multiplier

        # Add small penalty for sheer volume
        raw_score += max(0, len(findings) - 3) * 2.5

        # Normalize: define a reasonable max (e.g., 200) and clamp
        max_possible = 200.0
        normalized = int(min(100, round((raw_score / max_possible) * 100)))

        return normalized

    # ------------------------------------------------------------------ #
    # Remediation Roadmap builder
    # ------------------------------------------------------------------ #
    def build_remediation_roadmap(self, findings=None):
        """
        Produce a list of remediation entries from findings.
        Each remediation: {'action', 'priority', 'effort', 'impact'}
        Effort: Small / Medium / Large
        Priority: Critical / High / Medium / Low
        Impact: High / Medium / Low
        """
        if findings is None:
            findings = self.findings

        roadmap = []
        for f in findings:
            title = f.get('title') or f.get('description') or "Untitled issue"
            risk = (f.get('risk_level') or f.get('severity') or "medium").lower()

            # priority mapping
            if risk in ('critical', 'high'):
                priority = "Critical"
                effort = "Medium"
                impact = "High"
            elif risk in ('moderate', 'medium'):
                priority = "High"
                effort = "Medium"
                impact = "Medium"
            elif risk in ('low', 'info', 'informational'):
                priority = "Medium"
                effort = "Small"
                impact = "Low"
            else:
                priority = "High"
                effort = "Medium"
                impact = "Medium"

            # Construct action text deterministically
            action = None
            # Use category to suggest action
            category = (f.get('category') or "").lower()
            if any(k in title.lower() for k in ['cookie', 'consent', 'tracking']):
                action = "Implement granular cookie consent and block trackers prior to consent. Document cookie categories and retention periods."
            elif any(k in title.lower() for k in ['privacy policy', 'privacy notice']):
                action = "Publish an up-to-date privacy notice including lawful basis, retention schedule and data subject rights procedures."
            elif any(k in title.lower() for k in ['mfa', 'two-factor', '2fa']):
                action = "Enforce multifactor authentication for all privileged user accounts and admin portals."
            elif any(k in title.lower() for k in ['encryption', 'https', 'tls', 'certificate']):
                action = "Enforce TLS 1.2+/1.3, review cipher suites and enable HSTS. Ensure certificates are renewed automatically."
            elif any(k in title.lower() for k in ['incident', 'breach']):
                action = "Develop and test an Incident Response Plan; configure alerting and breach notification workflows."
            elif any(k in category for k in ['security', 'vulnerability', 'infrastructure']):
                action = "Perform vulnerability remediation: patching, hardening, and deploy a WAF. Run authenticated scans and schedule fixes."
            else:
                action = f"Investigate and remediate: {strip_tags(title)}. Document the change and validate via retest."

            roadmap.append({
                'action': action,
                'priority': priority,
                'effort': effort,
                'impact': impact,
            })

        # Deduplicate similar actions by action text (simple)
        seen = set()
        deduped = []
        for item in roadmap:
            key = item['action'][:140]
            if key not in seen:
                deduped.append(item)
                seen.add(key)

        return deduped

    # ------------------------------------------------------------------ #
    # Executive summary generator (deterministic, "AI-style" prose)
    # ------------------------------------------------------------------ #
    def build_executive_summary(self, findings=None, legal_exposure=None):
        """
        Build a professional, insurance-grade executive summary.
        Deterministic summary derived from report metrics and top issues.
        """
        if findings is None:
            findings = self.findings
        if legal_exposure is None:
            legal_exposure = self.calculate_legal_exposure(findings)

        total = len(findings)
        high_count = sum(1 for f in findings if (f.get('risk_level') or '').lower() in ('high','critical'))
        medium_count = sum(1 for f in findings if (f.get('risk_level') or '').lower() in ('medium','moderate'))
        low_count = sum(1 for f in findings if (f.get('risk_level') or '').lower() in ('low','info','informational'))

        top_3 = findings[:3] if findings else []
        top_issues_lines = []
        for f in top_3:
            title = f.get('title') or f.get('description') or "Unnamed issue"
            lvl = f.get('risk_level') or "Medium"
            top_issues_lines.append(f"- {title} ({lvl})")

        summary = []
        summary.append(f"This Executive Summary synthesizes the compliance and security posture observed for {self.scan.domain}.")
        summary.append(f"Overall compliance grade: {self.scan.grade or '—'}. Risk score: {self.scan.risk_score or '—'}%.")
        summary.append(f"Total identified issues: {total} (High/Critical: {high_count}; Medium: {medium_count}; Low: {low_count}).")
        if top_issues_lines:
            summary.append("Primary issues requiring immediate attention:")
            summary.extend(top_issues_lines)
        summary.append(f"The calculated Legal Exposure Index is {legal_exposure}/100. Higher values indicate increased regulatory and insurer risk.")
        summary.append("Recommended immediate actions: 1) Implement cookie consent and tracking controls; 2) Enforce MFA for privileged access; 3) Formalize incident response and breach notification flows.")
        summary.append("This report is intended for submission to cyber-underwriters and internal risk committees as evidence of a structured risk assessment and prioritized remediation plan.")

        # Join paragraphs into single text block
        return "\n\n".join(summary)

    # ------------------------------------------------------------------ #
    # PDF generator (passes the new computed fields to template)
    # ------------------------------------------------------------------ #
    def generate_pdf(self, request=None):
        """
        Generate PDF using reports/pdf_template.html and store into pdf_file.
        Adds computed context:
          - legal_exposure (int 0-100)
          - remediation (list)
          - executive_summary (string)
          - findings enhanced with gdpr_article
        """
        # Prepare findings and map GDPR
        findings = self.findings or []
        findings_mapped = self.map_gdpr_articles(findings)
        # Update internal findings with gdpr mapping (in-memory)
        self.findings = findings_mapped  # will call set_findings

        # Calculate legal exposure
        legal_exposure = self.calculate_legal_exposure(findings_mapped)

        # Build remediation roadmap
        remediation = self.build_remediation_roadmap(findings_mapped)

        # Executive summary
        executive_summary = self.build_executive_summary(findings_mapped, legal_exposure)

        # HOST RESOLUTION
        if request:
            current_host = request.get_host()
        else:
            # Fallback for Signals/Celery: use settings or a default
            current_host = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
            
        html_string = render_to_string('reports/pdf_template.html', {
            'report': self,
            'scan': self.scan,
            'firm': self.scan.firm,
            'generated_at': timezone.now(),
            'findings': findings_mapped,
            'recommendations': self.scan.raw_data.get('recommendations', []),
            'scan_duration': self.scan.scan_duration,
            'legal_exposure': legal_exposure,
            'remediation': remediation,
            'executive_summary': executive_summary,
            'host': current_host,
            'request': request,  # Can be None
        })

        # 2. FIX BASE_URL FOR ASSETS
        # If no request, base_url should point to local static files for WeasyPrint
        if request:
            base_url = request.build_absolute_uri('/')
        else:
            base_url = settings.STATIC_ROOT or settings.BASE_DIR

        pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf()

        #filename = f"report_{self.pk}_{self.scan.domain}_{self.scan.scan_id}.pdf"
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
    #if instance.status != "complete":
    if instance.status not in ["COMPLETED", "complete"]:
        return

    # Local import → prevents circular import
    from reports.models import ComplianceReport

    report, created_report = ComplianceReport.objects.get_or_create(scan=instance)

    # Copy findings from ScanResult.raw_data
    if created_report or not report.findings:
        findings = instance.raw_data.get('findings', [])
        report.findings = findings
        report.save(update_fields=['_findings'])

    # Generate PDF only if missing or outdated (you may change this logic if you prefer)
    # Always refresh computed fields before saving PDF
    report.generate_pdf()




class VerifiedReport(models.Model):
    report_id = models.CharField(max_length=16, unique=True)  # c054b193
    domain = models.CharField(max_length=255)
    audit_date = models.DateField()
    generated_at = models.DateTimeField()

    compliance_grade = models.CharField(max_length=4)  # D
    risk_score = models.IntegerField()                  # 92
    issues_found = models.IntegerField()                # 10

    frameworks = models.JSONField()                     # ["GDPR","OWASP","Supply Chain"]

    pdf_file = models.FileField(upload_to="reports/pdfs/")
    pdf_sha256 = models.CharField(max_length=64)

    scanner_signature = models.CharField(
        max_length=100,
        default="ComplyLaw AI Scanner"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report_id} | {self.domain}"


from django.db import models

class ReportVerification(models.Model):
    report_id = models.CharField(max_length=16, unique=True)
    domain = models.CharField(max_length=255)

    scan = models.ForeignKey(
        'scanner.ScanResult',
        on_delete=models.CASCADE,
        related_name='verifications'
    )

    generated_at = models.DateTimeField()
    pdf_file = models.FileField(upload_to='reports/pdfs/')
    pdf_sha256 = models.CharField(max_length=64)

    scanner_signature = models.CharField(
        max_length=100,
        default='ComplyLaw AI Scanner'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.report_id} | {self.domain}'

