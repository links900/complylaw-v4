# scanner/templatetags/scan_filters.py
from django import template

register = template.Library()


@register.filter
def select_gdpr(findings):
    """Return all findings related to GDPR"""
    if not findings:
        return []
    return [
        f for f in findings
        if f.get('module') == 'GDPR' or
           'GDPR' in f.get('standard', '') or
           'GDPR' in f.get('title', '') or
           'GDPR' in str(f.get('details', ''))
    ]


@register.filter
def select_owasp(findings):
    """Return all OWASP-related findings"""
    if not findings:
        return []
    return [
        f for f in findings
        if f.get('module') == 'OWASP' or
           'OWASP' in f.get('standard', '') or
           'OWASP' in f.get('title', '')
    ]


@register.filter
def select_iso(findings):
    if not findings:
        return []
    return [f for f in findings if 'ISO' in f.get('standard', '') or f.get('module') == 'ISO 27001']


@register.filter
def select_pci(findings):
    if not findings:
        return []
    return [f for f in findings if 'PCI' in f.get('standard', '') or f.get('module') == 'PCI DSS']


@register.filter
def select_hipaa(findings):
    if not findings:
        return []
    return [f for f in findings if 'HIPAA' in f.get('standard', '') or f.get('module') == 'HIPAA']


@register.filter
def has_issue(findings, keyword):
    """Check if any finding contains a keyword in title"""
    if not findings:
        return False
    return any(keyword.lower() in f.get('title', '').lower() for f in findings)
    
    

@register.filter
def safe_get(d, key_default):
    """
    Safely get a key from a dictionary.
    Usage in template: {{ f|safe_get:"standard,—" }}
    Supports nested keys with dot notation: "module.submodule"
    Format: "key,default_value"
    """
    if not isinstance(d, dict):
        return '—'

    try:
        parts = key_default.split(',', 1)
        key = parts[0].strip()
        default = parts[1].strip() if len(parts) > 1 else '—'

        # support nested keys: module.submodule
        keys = key.split('.')
        value = d
        for k in keys:
            value = value.get(k, None)
            if value is None:
                return default
        return value if value is not None else default
    except Exception:
        return '—'

