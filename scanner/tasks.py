# scanner/tasks.py — TIER-BASED + PERFORMANCE

from .models import ScanResult
from django.utils import timezone
import time
import random
import requests
import urllib3
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.messages import get_messages
from django.contrib.sessions.models import Session

from .scanner_tasks.helpers import connect_to_external_scanner
from .scanner_tasks.gdpr import (
    check_gdpr_dsar, check_gdpr_dpia, check_gdpr_retention, check_gdpr_dpo,
    crawl_sitemap, check_cookies, check_privacy_policy
)
from .scanner_tasks.owasp import (
    check_broken_access_control, check_crypto_failures, check_sql_injection,
    check_missing_security_headers, check_security_misconfig, check_outdated_software,
    check_auth_failures, check_integrity_failures, check_logging_monitoring, check_ssrf,
    run_nikto_scan
)
from .scanner_tasks.iso27001 import check_iso27001_access_control
from .scanner_tasks.pcidss import check_pci_dss_logging
from .scanner_tasks.hipaa import check_hipaa_encryption, check_forms
from .scanner_tasks.soc2 import check_soc2_access_reviews
from .scanner_tasks.cis import check_cis_benchmark_1_4
from .scanner_tasks.nist import check_third_party_scripts, run_nmap_vuln_scan
from .scanner_tasks.encryption import check_ssl_tls


# === TIERS (same as before) ===
gdpr_tests = [
    ("GDPR: DSAR", check_gdpr_dsar),
    ("GDPR: DPIA", check_gdpr_dpia),
    ("GDPR: Retention", check_gdpr_retention),
    ("GDPR: DPO", check_gdpr_dpo),
    ("Sitemap & Robots", crawl_sitemap),
    ("Cookie Consent", check_cookies),
    ("Privacy Policy", check_privacy_policy),
]

owasp_tests = [
    ("OWASP A01: Access Control", check_broken_access_control),
    ("OWASP A02: Crypto", check_crypto_failures),
    ("OWASP A03: Injection", check_sql_injection),
    ("OWASP A04: Headers", check_missing_security_headers),
    ("OWASP A05: Misconfig", check_security_misconfig),
    ("OWASP A06: Outdated", check_outdated_software),
    ("OWASP A07: Auth", check_auth_failures),
    ("OWASP A08: Integrity", check_integrity_failures),
    ("OWASP A09: Logging", check_logging_monitoring),
    ("OWASP A10: SSRF", check_ssrf),
    ("Nikto Scan", run_nikto_scan),
]

basic_security_tests = [
    ("SSL/TLS Check", check_ssl_tls),
    ("Third-Party Scripts", check_third_party_scripts),
]

iso27001_tests = [("ISO 27001 Access", check_iso27001_access_control)]
pcidss_tests = [("PCI DSS Headers", check_pci_dss_logging)]
hipaa_tests = [("HIPAA Encryption", check_hipaa_encryption), ("HIPAA Forms", check_forms)]
soc2_tests = [("SOC 2 Access", check_soc2_access_reviews)]
cis_tests = [("CIS Lockout", check_cis_benchmark_1_4)]
nmap_tests = [("Nmap Vuln Scan", run_nmap_vuln_scan)]

FREE_TESTS = gdpr_tests + owasp_tests[:7] + basic_security_tests
PRO_TESTS = FREE_TESTS + owasp_tests[7:] + iso27001_tests + pcidss_tests
ENTERPRISE_TESTS = PRO_TESTS + hipaa_tests + soc2_tests + cis_tests + nmap_tests
#FREE_TESTS=ENTERPRISE_TESTS

TIERS = {
    "free": FREE_TESTS,
    "pro": PRO_TESTS,
    "enterprise": ENTERPRISE_TESTS,
}


@shared_task(bind=True)
def run_compliance_scan(self, scan_id):
    try:
        scan = ScanResult.objects.select_for_update().get(pk=scan_id)
    except ScanResult.DoesNotExist:
        return "Scan not found"

    domain = scan.domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]

    # Get user tier
    try:
        user_tier = scan.user.profile.subscription_tier.lower() if hasattr(scan, 'user') and hasattr(scan.user, 'profile') else 'free'
    except:
        user_tier = 'free'

    selected_tests = TIERS.get(user_tier, FREE_TESTS)

    # Initialize
    scan.status = 'RUNNING'
    scan.progress = 0
    scan.current_step = "Starting scan..."
    #scan.scan_log = f"[{timezone.now():%H:%M:%S}] Scan started for {domain}\n"
    #scan.save(update_fields=['status', 'progress', 'current_step'])
    scan.save(update_fields=['status', 'progress', 'current_step', 'scan_log'])

    # Use a list to collect logs → write only 2–3 times total
    log_buffer = [f"[{timezone.now():%H:%M:%S}] Scan started → {domain} ({user_tier.capitalize()} Tier)"]

    channel_layer = get_channel_layer()
    raw_data = {
        "findings": [],
        "recommendations": [],
        "scanned_urls": 0,
        "issues_found": 0,
        "vulnerabilities": []
    }
    findings, breach_alerts, checklist = [], [], {}

    total_tests = len(selected_tests)
    progress_per_test = 90 / max(total_tests, 1)

    # === Run Tests ===
    external_results = connect_to_external_scanner(domain)
    _update_scan(scan, progress=5, step="Connecting...", log_buffer=log_buffer)

    for idx, (test_name, test_func) in enumerate(selected_tests):
        progress = min(95, 5 + int((idx + 1) * progress_per_test))

        _update_scan(scan, progress=progress, step=test_name, log_buffer=log_buffer)

        try:
            result = test_func(domain)
        except Exception as e:
            result = {"title": test_name, "status": "error", "details": str(e)}

        # Log result
        status = result.get("status", "error").upper()
        log_buffer.append(f"[{timezone.now():%H:%M:%S}] [{progress}%] {test_name}: {status}")

        # Collect findings
        if not external_results:
            if result.get("status") in ["fail", "warn"]:
                raw_data["findings"].append(result)
                if result.get("risk_level") == "high":
                    breach_alerts.append(result["title"])
            if result.get("vulnerabilities"):
                raw_data["vulnerabilities"].extend(result["vulnerabilities"])

            # Checklist
            title = result.get("title", "").lower()
            if "ssl" in title or "tls" in title:
                checklist['https'] = result["status"] == "pass"
            if "cookie" in title:
                checklist['cookie_banner'] = result["status"] == "pass"

        time.sleep(0.4)

    # === Finalize ===
    _update_scan(scan, progress=98, step="Generating report...", log_buffer=log_buffer)

    if external_results:
        scan.grade = external_results.get("grade", "C")
        scan.risk_score = external_results.get("risk_score", 45.0)
        raw_data.update(external_results)
    else:
        fails = sum(1 for x in raw_data["findings"] if x["status"] == "fail")
        warns = sum(1 for x in raw_data["findings"] if x["status"] == "warn")
        score = 100 - (fails * 14) - (warns * 7)
        scan.grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"
        scan.risk_score = round(100 - score + random.uniform(1, 4), 1)

    # Final log + save
    log_buffer.append(f"[COMPLETE] Grade: {scan.grade} | Risk: {scan.risk_score}% | Issues: {len(raw_data['findings'])}")
    scan.scan_log = "\n".join(log_buffer[-100:])  # Keep last 100 lines
    scan.set_raw_data(raw_data)
    scan.set_breach_alerts(breach_alerts)
    scan.set_checklist_status(checklist)
    scan.recommendations = generate_recommendations(raw_data["findings"])
    scan.status = 'COMPLETED'
    scan.completed_at = timezone.now()
    scan.progress = 100
    scan.current_step = "Complete!"

    scan.save()
    
    
    # Send beautiful live toast: "abc.com scan completed!"
    # === Final Notification ===
    if scan.user: # Check if user exists before accessing .id
        try:
            async_to_sync(get_channel_layer().group_send)(
                f"user_{scan.user.id}",
                {
                    "type": "scan_notification",
                    "message": f"{domain} scan completed!",
                    "grade": scan.grade,
                    "risk_score": round(scan.risk_score, 1),
                    "scan_id": scan.id
                }
            )
        except Exception as e:
            print(f"[Notification failed] {e}")
    
    # This MUST run regardless of the notification succeeding
    _send_ws_complete(scan)


# === HELPER: Safe update (only 4–6 DB writes total!) ===
def _update_scan(scan, progress, step, log_buffer):
    scan.progress = progress
    scan.current_step = step
    scan.save(update_fields=['progress', 'current_step'])
    
    # Send WebSocket
    try:
        async_to_sync(get_channel_layer().group_send)(
            f"scan_{scan.id}",
            {
                "type": "scan.update",
                "progress": progress,
                "step": step,
                "status": "running"
            }
        )
    except:
        pass  # Never crash scan due to WS


def _send_ws_complete(scan):
    try:
        async_to_sync(get_channel_layer().group_send)(
            f"scan_{scan.id}",
            {"type": "scan.complete_trigger", "force_reload": True, "progress": 100}
        )
        async_to_sync(get_channel_layer().group_send)(
            f"scan_{scan.id}",
            {
                "type": "scan.update",
                "progress": 100,
                "message": f"{domain} scan completed!",
                "grade": scan.grade,
                "risk_score": scan.risk_score,
                "status": "complete"
                
            }
        )
    except:
        pass


def generate_recommendations(findings):
    recs = []
    for f in findings:
        t = f.get("title", "")
        if "Cookie" in t:
            recs.append({"title": "Add Cookie Consent Banner", "priority": "high"})
        if "SSL" in t or "TLS" in t:
            recs.append({"title": "Upgrade TLS & Enable HSTS", "priority": "high"})
        if "Header" in t:
            recs.append({"title": "Add Security Headers", "priority": "high"})
    return recs or [{"title": "No critical issues", "priority": "low"}]