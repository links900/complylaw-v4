# scanner_tasks/gdpr.py

from .helpers import _find_link, _fetch_page_text
import requests
import urllib3

def check_gdpr_dsar(domain: str):
    url = _find_link(domain, ["dsar", "data subject", "access my data"])
    text = _fetch_page_text(f"https://{domain}")
    found = any(k in text for k in ["dsar", "data subject access request"])
    status = "pass" if found or url else "fail"
    return {
        "title": "DSAR Endpoint (GDPR Art. 15)",
        "status": status,
        "details": f"DSAR page: {'Found' if url else 'Missing'}",
        "standard": "GDPR Art. 15",
        "risk_level": "high" if status == "fail" else "low",
        "module": "GDPR",
    }

def check_gdpr_dpia(domain: str):
    policy_url = _find_link(domain, ["privacy policy", "privacy"])
    if not policy_url:
        return {
            "title": "DPIA Reference (GDPR Art. 35)",
            "status": "fail",
            "details": "Privacy policy missing",
            "standard": "GDPR Art. 35",
            "risk_level": "high",
            "module": "GDPR",
        }
    text = _fetch_page_text(policy_url)
    found = any(p in text for p in ["dpia", "data protection impact assessment"])
    status = "pass" if found else "warn"
    return {
        "title": "DPIA Mentioned (GDPR Art. 35)",
        "status": status,
        "details": f"DPIA reference: {'Found' if found else 'Missing'}",
        "standard": "GDPR Art. 35",
        "risk_level": "high" if status == "warn" else "low",
        "module": "GDPR",
    }

def check_gdpr_retention(domain: str):
    policy_url = _find_link(domain, ["privacy policy"])
    if not policy_url:
        return {
            "title": "Retention Policy (GDPR Art. 5)",
            "status": "fail",
            "details": "Policy missing",
            "standard": "GDPR Art. 5(1)(e)",
            "risk_level": "high",
            "module": "GDPR",
        }
    text = _fetch_page_text(policy_url)
    found = any(p in text for p in ["retention period", "data will be deleted"])
    status = "pass" if found else "warn"
    return {
        "title": "Data Retention Policy",
        "status": status,
        "details": f"Retention clause: {'Present' if found else 'Missing'}",
        "standard": "GDPR Art. 5(1)(e)",
        "risk_level": "high" if status == "warn" else "low",
        "module": "GDPR",
    }

def check_gdpr_dpo(domain: str):
    policy_url = _find_link(domain, ["privacy", "contact"])
    if not policy_url:
        return {
            "title": "DPO Contact (GDPR Art. 37)",
            "status": "fail",
            "details": "No policy",
            "standard": "GDPR Art. 37",
            "risk_level": "high",
            "module": "GDPR",
        }
    text = _fetch_page_text(policy_url)
    found = any(p in text for p in ["data protection officer", "dpo"])
    status = "pass" if found else "warn"
    return {
        "title": "DPO Appointed",
        "status": status,
        "details": f"DPO contact: {'Found' if found else 'Not mentioned'}",
        "standard": "GDPR Art. 37",
        "risk_level": "medium",
        "module": "GDPR",
    }

def crawl_sitemap(domain):
    try:
        sitemap_ok = requests.head(f"https://{domain}/sitemap.xml", timeout=10, verify=True).status_code == 200
        robots_ok = requests.head(f"https://{domain}/robots.txt", timeout=10, verify=True).status_code == 200
        status = "pass" if sitemap_ok and robots_ok else "warn"
        return {
            "title": "Sitemap & Robots",
            "status": status,
            "details": f"Sitemap: {'OK' if sitemap_ok else 'Missing'} | Robots: {'OK' if robots_ok else 'Missing'}",
            "standard": "GDPR Art. 35",
            "module": "GDPR",
        }
    except:
        return {"title": "Sitemap", "status": "warn", "details": "Not accessible", "module": "GDPR"}

def check_cookies(domain):
    try:
        response = requests.get(f"https://{domain}", timeout=10, verify=True)
        banner = any(x in response.text.lower() for x in ["cookie", "consent"])
        status = "pass" if banner else "fail"
        return {
            "title": "Cookie Consent",
            "status": status,
            "details": f"Banner: {'Detected' if banner else 'Missing'}",
            "standard": "GDPR Art. 7",
            "risk_level": "high" if not banner else "low",
            "module": "GDPR",
        }
    except:
        return {"title": "Cookies", "status": "fail", "details": "Site down", "module": "GDPR"}

def check_privacy_policy(domain):
    try:
        policy_url = _find_link(domain, ["privacy", "policy"])
        if not policy_url:
            return {"title": "Privacy Policy", "status": "fail", "details": "Not found", "module": "GDPR"}
        text = _fetch_page_text(policy_url)
        gdpr_score = sum(1 for k in ['gdpr', 'controller', 'erase', 'dpo'] if k in text)
        ccpa = any(k in text for k in ['ccpa', 'california'])
        status = "pass" if gdpr_score >= 2 and ccpa else "warn"
        return {
            "title": "Privacy Policy",
            "status": status,
            "details": f"GDPR: {gdpr_score}/4 | CCPA: {'Yes' if ccpa else 'No'}",
            "standard": "GDPR, CCPA",
            "module": "GDPR",
        }
    except:
        return {"title": "Policy", "status": "fail", "details": "Error", "module": "GDPR"}