from django import template
register = template.Library()

@register.filter
def dict_key(d, key):
    """Returns the value for a given key in a dictionary."""
    try:
        return d.get(key, {})
    except (AttributeError, TypeError):
        return {}