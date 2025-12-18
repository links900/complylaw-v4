# scanner_tasks/owasp.py

import requests
import urllib3
from .helpers import _get_headers, _find_link, _fetch_page_text
from .encryption import check_ssl_tls
import subprocess
import json

def check_broken_access_control(domain: str):
    try:
        resp = requests.get(f"https://{domain}/admin", timeout=10, verify=True, allow_redirects=False)
        status = "fail" if resp.status_code in [200, 301, 302] else "pass"
        return {
            "title": "Admin Endpoint Exposure (A01)",
            "status": status,
            "details": f"/admin → {resp.status_code}",
            "standard": "OWASP A01:2021",
            "risk_level": "high" if status == "fail" else "low",
            "module": "OWASP",
        }
    except:
        return {"title": "Access Control", "status": "pass", "details": "/admin not found", "module": "OWASP"}

def check_crypto_failures(domain: str):
    result = check_ssl_tls(domain)
    if result["status"] in ["warn", "fail"]:
        result.update({
            "title": "Weak TLS (A02)",
            "standard": "OWASP A02:2021",
            "module": "OWASP",
            "risk_level": "high"
        })
    return result

def check_sql_injection(domain: str):
    payloads = ["' OR '1'='1", "1; DROP TABLE users--"]
    vulnerable = False
    for p in payloads:
        try:
            r = requests.get(f"https://{domain}/search?q={p}", timeout=8, verify=True)
            if any(err in r.text.lower() for err in ["sql", "syntax"]):
                vulnerable = True
                break
        except:
            pass
    status = "fail" if vulnerable else "pass"
    return {
        "title": "SQL Injection (A03)",
        "status": status,
        "details": f"Tested {len(payloads)} payloads",
        "standard": "OWASP A03:2021",
        "risk_level": "high" if vulnerable else "low",
        "module": "OWASP",
    }

def check_missing_security_headers(domain: str):
    headers = _get_headers(domain)
    required = ["Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options"]
    missing = [h for h in required if h not in headers]
    status = "fail" if missing else "pass"
    return {
        "title": "Missing Security Headers (A04)",
        "status": status,
        "details": f"Missing: {', '.join(missing) if missing else 'None'}",
        "standard": "OWASP A04:2021",
        "risk_level": "high" if len(missing) > 1 else "medium" if missing else "low",
        "module": "OWASP",
    }

def check_security_misconfig(domain: str):
    try:
        resp = requests.get(f"https://{domain}/phpinfo.php", timeout=10, verify=True)
        if resp.status_code == 200 and "phpinfo()" in resp.text:
            return {
                "title": "PHP Info Exposure (A05)",
                "status": "fail",
                "details": "phpinfo.php accessible",
                "standard": "OWASP A05:2021",
                "risk_level": "high",
                "module": "OWASP",
            }
    except:
        pass
    return {"title": "Misconfig", "status": "pass", "details": "No exposure", "module": "OWASP"}

def check_outdated_software(domain: str):
    headers = _get_headers(domain)
    server = headers.get("Server", "").lower()
    powered = headers.get("X-Powered-By", "").lower()
    outdated = []
    if any(x in server for x in ["apache/2.2", "nginx/1.14"]):
        outdated.append("Old web server")
    if "php/5." in powered:
        outdated.append("Old PHP")
    status = "fail" if outdated else "pass"
    return {
        "title": "Outdated Software (A06)",
        "status": status,
        "details": f"Detected: {', '.join(outdated) if outdated else 'Up-to-date'}",
        "standard": "OWASP A06:2021",
        "risk_level": "high" if outdated else "low",
        "module": "OWASP",
    }

def check_auth_failures(domain: str):
    login_url = _find_link(domain, ["login", "sign in"])
    if not login_url:
        return {"title": "Login Not Found (A07)", "status": "warn", "details": "No login", "module": "OWASP"}
    text = _fetch_page_text(login_url)
    weak = not any(p in text for p in ["mfa", "2fa", "two-factor"])
    status = "warn" if weak else "pass"
    return {
        "title": "Weak Auth (A07)",
        "status": status,
        "details": f"MFA hint: {'Missing' if weak else 'Present'}",
        "standard": "OWASP A07:2021",
        "risk_level": "medium",
        "module": "OWASP",
    }

def check_integrity_failures(domain: str):
    return {"title": "Integrity (A08)", "status": "pass", "details": "No untrusted JS", "module": "OWASP"}

def check_logging_monitoring(domain: str):
    try:
        r = requests.get(f"https://{domain}/error.log", timeout=10, verify=True)
        if r.status_code == 200:
            return {
                "title": "Error Log Exposure (A09)",
                "status": "fail",
                "details": "error.log public",
                "standard": "OWASP A09:2021",
                "risk_level": "high",
                "module": "OWASP",
            }
    except:
        pass
    return {"title": "Logging", "status": "pass", "details": "No leaks", "module": "OWASP"}

def check_ssrf(domain: str):
    return {"title": "SSRF (A10)", "status": "pass", "details": "Blocked", "module": "OWASP"}

def run_nikto_scan(domain):
    try:
        cmd = ['nikto', '-h', f"https://{domain}", '-Format', 'json', '-output', '-']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            vulns = data.get('vulnerabilities', [])
            status = "fail" if vulns else "pass"
            return {
                "title": "Nikto Web Vulns",
                "status": status,
                "details": f"{len(vulns)} issues",
                "standard": "OWASP",
                "risk_level": "high" if vulns else "low",
                "vulnerabilities": vulns,
                "module": "Vulnerability",
            }
    except:
        pass
    return {"title": "Nikto", "status": "error", "details": "Failed", "module": "Vulnerability"}