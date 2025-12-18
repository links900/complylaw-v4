# scanner_tasks/hipaa.py

from .encryption import check_ssl_tls
import requests
import urllib3
from bs4 import BeautifulSoup

def check_hipaa_encryption(domain: str):
    result = check_ssl_tls(domain)
    result["module"] = "HIPAA"
    result["standard"] = "HIPAA §164.312"
    return result

def check_forms(domain):
    try:
        response = requests.get(f"https://{domain}", timeout=10, verify=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        forms = soup.find_all('form')
        encrypted = all(f.get('action', '').startswith('https') for f in forms if f.get('action'))
        status = "pass" if encrypted else "fail"
        return {
            "title": "Data Forms",
            "status": status,
            "details": f"{len(forms)} forms | HTTPS: {'Yes' if encrypted else 'No'}",
            "standard": "HIPAA",
            "module": "HIPAA",
        }
    except:
        return {"title": "Forms", "status": "error", "details": "Failed", "module": "HIPAA"}