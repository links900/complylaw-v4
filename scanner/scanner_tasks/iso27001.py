# scanner_tasks/iso27001.py

from .helpers import _find_link, _fetch_page_text

def check_iso27001_access_control(domain: str):
    policy_url = _find_link(domain, ["terms", "aup"])
    if not policy_url:
        return {"title": "Access Policy (ISO)", "status": "warn", "details": "Missing", "standard": "ISO A.9", "module": "ISO 27001"}
    text = _fetch_page_text(policy_url)
    found = "registration" in text
    status = "pass" if found else "warn"
    return {
        "title": "User Access Policy",
        "status": status,
        "details": f"Defined: {'Yes' if found else 'No'}",
        "standard": "ISO 27001 A.9.2.1",
        "module": "ISO 27001",
    }