# scanner_tasks/cis.py

def check_cis_benchmark_1_4(domain: str):
    return {
        "title": "Account Lockout (CIS)",
        "status": "warn",
        "details": "Not detected",
        "standard": "CIS 1.4",
        "module": "CIS",
    }