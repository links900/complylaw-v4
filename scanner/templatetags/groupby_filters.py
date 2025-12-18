# scanner/templatetags/scan_filters.py
from django import template
from itertools import groupby
from operator import itemgetter
from collections import defaultdict

register = template.Library()


@register.filter
def select_gdpr(findings):
    if not findings:
        return []
    return [
        f for f in findings
        if 'GDPR' in f.get('standard', '') or 'GDPR' in f.get('title', '')
    ]

@register.filter
def select_ccpa(findings):
    if not findings:
        return []
    return [
        f for f in findings
        if 'CCPA' in f.get('standard', '') or 'CCPA' in f.get('title', '')
    ]

@register.filter
def select_iso(findings):
    return [f for f in findings if 'ISO' in f.get('standard', '')] if findings else []

@register.filter
def select_nist(findings):
    return [f for f in findings if 'NIST' in f.get('standard', '')] if findings else []
    
    
# scanner/templatetags/groupby_filters.py
from django import template
from collections import defaultdict

register = template.Library()

@register.filter
def groupby_module(findings):
    groups = defaultdict(list)
    for f in findings:
        module = f.get('module', 'Unknown')
        groups[module].append(f)
    
    result = []
    for module, items in sorted(groups.items(), key=lambda x: x[0]):
        result.append({
            'module': module,
            'items': items
        })
    return result