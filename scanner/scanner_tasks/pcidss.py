# scanner_tasks/pcidss.py

from .helpers import _get_headers

def check_pci_dss_logging(domain: str):
    headers = _get_headers(domain)
    leaked = any(k in headers.get("Server", "") for k in ["Apache", "nginx", "IIS"])
    status = "fail" if leaked else "pass"
    return {
        "title": "Server Header Leak (PCI)",
        "status": status,
        "details": f"Server: {headers.get('Server', 'Hidden')}",
        "standard": "PCI DSS 10.2",
        "risk_level": "high" if leaked else "low",
        "module": "PCI DSS",
    }