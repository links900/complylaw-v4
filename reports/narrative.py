#reports\narrative.py
class NarrativeService:
    @staticmethod
    def get_executive_summary(score_data):
        score = score_data['score']
        high_gaps = score_data['risk_summary']['HIGH']
        med_gaps = score_data['risk_summary']['MEDIUM']
        
        # Determine Status and Tone
        if score >= 90 and high_gaps == 0:
            status = "EXEMPLARY"
            tone_css = "success"
            message = (
                f"The organization demonstrates a robust compliance posture with a unified score of {score}%. "
                "Technical controls align with governance frameworks, showing minimal residual risk."
            )
        elif score >= 70 and high_gaps == 0:
            status = "FUNCTIONAL"
            tone_css = "warning"
            message = (
                f"The organization meets the baseline requirements for compliance with a score of {score}%. "
                f"However, {med_gaps} medium-priority governance gaps were identified that require a remediation roadmap."
            )
        else:
            status = "NON-COMPLIANT / AT RISK"
            tone_css = "danger"
            message = (
                f"Critical compliance failures detected. With {high_gaps} HIGH-impact gaps, the organization "
                "is currently exposed to significant regulatory and security risks. Immediate intervention is required."
            )

        return {
            "status_label": status,
            "tone_css": tone_css,
            "narrative": message
        }