# scanner_tasks/encryption.py

import socket
import ssl
from cryptography import x509
from cryptography.hazmat.backends import default_backend

def check_ssl_tls(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert(binary_form=True)
                x509_cert = x509.load_der_x509_certificate(cert, default_backend())
                expiry = x509_cert.not_valid_after_utc.date()
                protocol = ssock.version()
                cipher = ssock.cipher()[0]
                status = "pass" if protocol in ["TLSv1.3", "TLSv1.2"] and "RSA" not in cipher else "warn"
                return {
                    "title": "SSL/TLS",
                    "status": status,
                    "details": f"{protocol} | {cipher} | Expires: {expiry}",
                    "standard": "PCI DSS Req 4.1",
                    "module": "Encryption",
                }
    except Exception as e:
        return {"title": "SSL/TLS", "status": "fail", "details": f"Error: {str(e)}", "module": "Encryption"}