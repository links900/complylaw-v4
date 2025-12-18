# reports/utils.py
import hashlib

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()



def calculate_sha256_bytes(data: bytes) -> str:
    sha = hashlib.sha256()
    sha.update(data)
    return sha.hexdigest()



def get_unified_report_data(scan_id):
    scan = Scan.objects.get(id=scan_id)
    org_audit = getattr(scan, 'manual_audit', None)
    
    # 1. Technical (Scanner)
    tech_score = scan.score 
    
    # 2. Organizational (Checklist)
    org_score = 100
    risk_summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    
    if org_audit:
        org_score = ScoringService.calculate_org_score(org_audit)
        # Count gaps for the Executive Summary
        gaps = org_audit.responses.filter(status='no')
        for gap in gaps:
            risk_summary[gap.template.risk_impact] += 1

    # 3. Final Combined Weighted Score
    # Enterprise Standard: 40% Tech / 60% Policy
    final_score = (tech_score * 0.4) + (org_score * 0.6)
    
    return {
        "score": round(final_score, 2),
        "tech_score": tech_score,
        "org_score": round(org_score, 2),
        "risk_summary": risk_summary,
        "is_compliant": final_score > 70
    }
    

def get_top_priorities(submission):
    # Fetch the 3 heaviest controls that failed
    priorities = submission.responses.filter(status='no').select_related('template').order_by('-template__weight')[:3]
    return priorities
    
    
import hashlib

def generate_report_hash(file_path):
    """Creates a SHA-256 fingerprint of the PDF file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()