from django.conf import settings
from django.conf.urls.defaults import url, include

def trailing_slash():
    if getattr(settings, 'TASTYPIE_ALLOW_MISSING_SLASH', False):
        return '/?'
    
    return '/'

#        if nest:
#            regex += r"(?P<tastypie_nesting>/.*[^/])?"
