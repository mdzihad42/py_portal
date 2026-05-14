from django import template

register = template.Library()

@register.filter
def format_duration(seconds):
    if not seconds:
        return "0s"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)

@register.filter
def get_item(dictionary, key):
    if dictionary:
        return dictionary.get(key)
    return None
