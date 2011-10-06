from django.conf import settings
from django.conf.urls.defaults import url, include

def trailing_slash():
    if getattr(settings, 'TASTYPIE_ALLOW_MISSING_SLASH', False):
        return '/?'
    
    return '/'

class TastypieUrl(object):
    """
    A structure class to return properly generated urls with nesting support.
    """
    
    def __init__(self, resource, regex, view, kwargs=None, name=None, prefix='', nest=False):
        """
        Resource is the nested resource
        Regex is the url pattern
        View is the parent view this url points to if not nested
        Name is the name of the parent pattern
        Prefix is any prefix of the pattern
        Nest controls if nesting is enabled
        """
        self.resource = resource
        self.resource_name = resource._meta.resource_name
        
        # If nesting is enabled, capture extra url parts
        if nest:
            regex += r"(?P<tastypie_nesting>/.*[^/])?"
        
        self.regex = regex + trailing_slash() + r"$"
        self.view = view
        self.kwargs = kwargs
        self.name = name
        self.prefix = prefix
        self.nest = nest

    def nested_urls(self):
        """
        Utility function, adds the parent url to the nested urls
        """
        return [url(r"", self.view, self.kwargs, self.name, self.prefix)]
        + self.resource.nested_urls()
    
    def prefix_url(self):
        """
        The url with the resource name prefixed in front for normal matching
        """
        if self.nest:
            return (r"^(?P<resource_name>%s)" % self.resource_name + self.regex, include(self.nested_urls()))
        else:
            return url(r"^(?P<resource_name>%s)" % self.resource_name + self.regex, self.view,
                   self.kwargs, self.name, self.prefix) 
        
    def raw_url(self):
        """
        The urls without the prefix in front.
        
        TODO: why do I need this
        """
        if self.nest:
            return (self.regex, include(self.nested_urls()))
        else:
            return url(self.regex, self.view,
                   self.kwargs, self.name, self.prefix)

tp_url = TastypieUrl

