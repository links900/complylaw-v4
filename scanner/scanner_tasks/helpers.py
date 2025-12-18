# scanner_tasks/helpers.py

import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SCANNER_API_URL = "https://api.complylaw-scanner.com/v1/scan"
SCANNER_API_KEY = "your-api-key-here"

# Optional: suppress warnings only if you want to ignore SSL issues
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def connect_to_external_scanner(domain: str):
    if SCANNER_API_KEY == "your-api-key-here" or not SCANNER_API_URL:
        return None
    try:
        payload = {"domain": domain, "api_key": SCANNER_API_KEY}
        resp = requests.post(SCANNER_API_URL, json=payload, timeout=10, verify=True)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def _fetch_page_text(url: str, timeout: int = 10) -> str:
    """Fetch page text safely with SSL verification"""
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True, verify=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ").lower()
    except Exception:
        return ""

def _find_link(domain: str, keywords: list, base_url: str | None = None) -> str | None:
    """Find first <a> link containing any of the keywords"""
    if not base_url:
        base_url = f"https://{domain}"
    try:
        r = requests.get(base_url, timeout=10, allow_redirects=True, verify=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if any(k in a.get_text(strip=True).lower() for k in keywords):
                return urljoin(base_url, a["href"])
    except Exception:
        pass
    return None

def _get_headers(domain: str):
    """Return headers with SSL verification"""
    try:
        r = requests.head(f"https://{domain}", timeout=10, allow_redirects=True, verify=True)
        return r.headers
    except:
        return {}
