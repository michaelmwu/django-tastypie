"""
Handling of media types, as found in HTTP Content-Type and Accept headers.

See http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7
"""

import mimeparse

def media_type_matches(lhs, rhs):
    """
    Returns ``True`` if the media type in the first argument <= the
    media type in the second argument.  The media types are strings
    as described by the HTTP spec.

    Valid media type strings include:

    'application/json; indent=4'
    'application/json'
    'text/*'
    '*/*'
    """
    
    # Result of best match is a matching mimetype, or '' if no match is found
    return len(mimeparse.best_match([rhs], lhs)) > 0

def determine_format(request, serializer, default_format='application/json'):
    """
    Tries to "smartly" determine which output format is desired.
    
    First attempts to find a ``format`` override from the request and supplies
    that if found.
    
    If no request format was demanded, it falls back to ``mimeparse`` and the
    ``Accepts`` header, allowing specification that way.
    
    If still no format is found, returns the ``default_format`` (which defaults
    to ``application/json`` if not provided).
    """
    # First, check if they forced the format.
    if request.GET.get('format'):
        if request.GET['format'] in serializer.formats:
            return serializer.get_mime_for_format(request.GET['format'])
    
    # If callback parameter is present, use JSONP.
    if request.GET.has_key('callback'):
        return serializer.get_mime_for_format('jsonp')
    
    # Try to fallback on the Accepts header.
    if request.META.get('HTTP_ACCEPT', '*/*') != '*/*':
        formats = list(serializer.supported_formats) or []
        # Reverse the list, because mimeparse is weird like that. See also
        # https://github.com/toastdriven/django-tastypie/issues#issue/12 for
        # more information.
        formats.reverse()
        best_format = mimeparse.best_match(formats, request.META['HTTP_ACCEPT'])
        
        if best_format:
            return best_format
    
    # No valid 'Accept' header/formats. Sane default.
    return default_format


def build_content_type(format, encoding='utf-8'):
    """
    Appends character encoding to the provided format if not already present.
    """
    if 'charset' in format:
        return format
    
    return "%s; charset=%s" % (format, encoding)
