#checklists\services.py


from .models import ChecklistSubmission

class ScoringService:
    RISK_WEIGHTS = {'HIGH': 3.0, 'MEDIUM': 2.0, 'LOW': 1.0}

    @staticmethod
    def calculate(submission_id):
        sub = ChecklistSubmission.objects.select_related('scan').get(id=submission_id)
        # Handle the fact that 'risk_score' might be null in the model
        tech_score = sub.scan.risk_score if sub.scan.risk_score is not None else 0
        org_score = ScoringService.calculate_org_score(sub)
        
        final_score = (tech_score * 0.6) + (org_score * 0.4)
        
        return {
            "tech": round(tech_score, 2),
            "org": round(org_score, 2),
            "total": round(final_score, 2),
            "grade": ScoringService.get_grade(final_score)
        }

    @staticmethod
    def calculate_org_score(submission):
        total_possible = 0
        total_earned = 0
        responses = submission.responses.select_related('template').all()
        
        for res in responses:
            multiplier = ScoringService.RISK_WEIGHTS.get(res.template.risk_impact, 1.0)
            item_weight = res.template.weight * multiplier
            total_possible += item_weight
            
            if res.status == 'yes':
                total_earned += item_weight
            elif res.status == 'partial':
                total_earned += (item_weight * 0.5)

        return (total_earned / total_possible * 100) if total_possible > 0 else 100

    @staticmethod
    def get_grade(score):
        if score >= 90: return "A"
        if score >= 75: return "B"
        if score >= 60: return "C"
        return "D"