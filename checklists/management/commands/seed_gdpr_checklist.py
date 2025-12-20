#checklists\managment\commands\seed_compliance.py
from django.core.management.base import BaseCommand
from checklists.models import ChecklistTemplate, RiskImpact

class Command(BaseCommand):
    help = 'Seeds the database with GDPR Checklist Templates'

    def handle(self, *args, **kwargs):
        seed_gdpr_checklist = [
            {
                "standard": "GDPR",
                "code": "GDPR-01",
                "reference_article": "Article 30",
                "title": "Record of Processing Activities (ROPA)",
                "description": "The organization must maintain a central registry of all personal data processing activities, including purposes, data categories, and retention periods.",
                "risk_impact": "HIGH",
                "weight": 2.0,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-02",
                "reference_article": "Articles 12, 13, 14",
                "title": "Privacy Notice & Transparency",
                "description": "External and internal privacy notices must be concise, transparent, and provide information on how data is collected, used, and stored.",
                "risk_impact": "HIGH",
                "weight": 1.5,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-03",
                "reference_article": "Article 6",
                "title": "Lawfulness of Processing",
                "description": "A valid legal basis (Consent, Contract, Legal Obligation, Vital Interests, Public Task, or Legitimate Interests) must be identified for every processing activity.",
                "risk_impact": "HIGH",
                "weight": 1.5,
                "requires_evidence": False
            },
            {
                "standard": "GDPR",
                "code": "GDPR-04",
                "reference_article": "Article 32",
                "title": "Security of Processing (TOMs)",
                "description": "Implementation of Technical and Organizational Measures (TOMs) such as encryption, pseudonymization, 2FA, and regular security testing.",
                "risk_impact": "HIGH",
                "weight": 2.0,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-05",
                "reference_article": "Article 35",
                "title": "Data Protection Impact Assessment (DPIA)",
                "description": "Process for conducting assessments for processing operations likely to result in a high risk to the rights and freedoms of individuals.",
                "risk_impact": "HIGH",
                "weight": 2.0,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-06",
                "reference_article": "Articles 15-22",
                "title": "Data Subject Rights Procedure",
                "description": "Established workflows to handle requests for access (DSAR), rectification, erasure (Right to be Forgotten), and data portability within 30 days.",
                "risk_impact": "MEDIUM",
                "weight": 1.0,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-07",
                "reference_article": "Articles 33 & 34",
                "title": "Data Breach Notification Protocol",
                "description": "Internal procedure to detect, investigate, and report data breaches to the Supervisory Authority within 72 hours and to affected individuals.",
                "risk_impact": "HIGH",
                "weight": 1.5,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-08",
                "reference_article": "Article 28",
                "title": "Processor & Third-Party Contracts",
                "description": "Presence of Data Processing Agreements (DPAs) with all vendors and third-party processors that handle personal data.",
                "risk_impact": "MEDIUM",
                "weight": 1.2,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-09",
                "reference_article": "Article 37",
                "title": "DPO Appointment & Governance",
                "description": "Designation of a Data Protection Officer if required, or documentation explaining why a DPO is not mandatory for the organization.",
                "risk_impact": "LOW",
                "weight": 0.8,
                "requires_evidence": False
            },
            {
                "standard": "GDPR",
                "code": "GDPR-10",
                "reference_article": "Articles 44-49",
                "title": "International Data Transfers",
                "description": "Mechanism for ensuring adequate protection for data transferred outside the EEA/UK (e.g., Standard Contractual Clauses or Adequacy Decisions).",
                "risk_impact": "HIGH",
                "weight": 1.5,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-11",
                "reference_article": "Article 5(1)(e)",
                "title": "Data Retention & Disposal Policy",
                "description": "A formal policy and schedule defining how long different categories of personal data are kept and how they are securely deleted.",
                "risk_impact": "MEDIUM",
                "weight": 1.0,
                "requires_evidence": True
            },
            {
                "standard": "GDPR",
                "code": "GDPR-12",
                "reference_article": "Article 25",
                "title": "Privacy by Design & Default",
                "description": "Evidence that data protection is integrated into system development and business processes from the outset.",
                "risk_impact": "MEDIUM",
                "weight": 1.0,
                "requires_evidence": False
            }
        ]

        for item in seed_gdpr_checklist:
            ChecklistTemplate.objects.update_or_create(
                standard="GDPR",
                code=item['code'],
                defaults={
                    "reference_article": item['reference_article'],
                    "title": item['title'],
                    "description": item['description'],
                    "risk_impact": item['risk_impact'],
                    "requires_evidence": item['requires_evidence'],
                    "active": True
                }
            )
        self.stdout.write(self.style.SUCCESS('Successfully seeded GDPR checklist'))