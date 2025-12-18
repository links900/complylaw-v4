#checklists\managment\commands\seed_compliance.py
from django.core.management.base import BaseCommand
from checklists.models import ChecklistTemplate, RiskImpact

class Command(BaseCommand):
    help = 'Seeds professional compliance controls'

    def handle(self, *args, **kwargs):
        data = [
            # GDPR CONTROLS
            {
                "standard": "GDPR", "code": "GDPR-SEC-01", 
                "ref": "Article 32", "title": "Encryption of Personal Data",
                "risk": RiskImpact.HIGH, "weight": 3.0,
                "desc": "Are technical measures (AES-256) used to encrypt data at rest?"
            },
            {
                "standard": "GDPR", "code": "GDPR-GOV-01", 
                "ref": "Article 37", "title": "Designation of DPO",
                "risk": RiskImpact.MEDIUM, "weight": 2.0,
                "desc": "Has a Data Protection Officer been formally appointed?"
            },
            # ISO 27001 CONTROLS
            {
                "standard": "ISO27001", "code": "A.5.1.1", 
                "ref": "Annex A.5.1.1", "title": "Information Security Policies",
                "risk": RiskImpact.HIGH, "weight": 3.0,
                "desc": "Is there a suite of policies approved by management?"
            }
        ]
        for item in data:
            ChecklistTemplate.objects.get_or_create(
                code=item['code'],
                defaults={
                    'standard': item['standard'],
                    'reference_article': item['ref'],
                    'title': item['title'],
                    'risk_impact': item['risk'],
                    'weight': item['weight'],
                    'description': item['desc']
                }
            )
        self.stdout.write(self.style.SUCCESS('Compliance controls seeded.'))