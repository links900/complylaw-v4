# scanner_tasks/nist.py

import nmap
import requests
import urllib3
from bs4 import BeautifulSoup

def check_third_party_scripts(domain):
    try:
        response = requests.get(f"https://{domain}", timeout=10, verify=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        external = [s['src'] for s in soup.find_all('script', src=True) if domain not in s['src']]
        status = "warn" if len(external) > 8 else "pass"
        return {
            "title": "Third-Party Scripts",
            "status": status,
            "details": f"{len(external)} external",
            "standard": "NIST",
            "module": "Supply Chain",
        }
    except:
        return {"title": "Scripts", "status": "error", "details": "Failed", "module": "Supply Chain"}

def run_nmap_vuln_scan(domain):
    try:
        nm = nmap.PortScanner()
        nm.scan(domain, arguments='--top-ports 100 -sV --script vuln')
        vulns = []
        for host in nm.all_hosts():
            for proto in nm[host].all_protocols():
                for port in nm[host][proto].keys():
                    if 'script' in nm[host][proto][port]:
                        for script, out in nm[host][proto][port]['script'].items():
                            if 'CVE' in out:
                                vulns.append({"cve": script, "port": port, "details": out})
        status = "fail" if vulns else "pass"
        return {
            "title": "Nmap Vulnerabilities",
            "status": status,
            "details": f"{len(vulns)} CVEs",
            "standard": "NIST",
            "risk_level": "high" if vulns else "low",
            "vulnerabilities": vulns,
            "module": "Vulnerability",
        }
    except:
        return {"title": "Nmap", "status": "error", "details": "Failed", "module": "Vulnerability"}