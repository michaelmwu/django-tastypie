"""
The :mod:`response` module provides Response classes you can use in your 
views to return a certain HTTP response. Typically a response is *rendered* 
into a HTTP response depending on what renderers are set on your view and
als depending on the accept header of the request. 
"""

import datetime
import httplib

from django.conf import settings
from django.core.handlers.wsgi import STATUS_CODE_TEXT
from django.http import BadHeaderError, SimpleCookie
from django.utils.encoding import smart_str

__all__ = ('Response', 'ErrorResponse')

class HttpHeaders(object):
    status_code = httplib.OK
    
    def __init__(self, status=None, headers=None):
        print "HEADERS INIT"
        # _headers is a mapping of the lower-case name to the original case of
        # the header (required for working with legacy systems) and the header
        # value.  Both the name of the header and its value are ASCII strings.
        self._headers = headers or {}
        self._charset = settings.DEFAULT_CHARSET
        self.cookies = SimpleCookie()
        if status:
            self.status_code = status
    
        #self.media_type = None
 
    @property
    def status_text(self):
        """
        Return reason text corresponding to our HTTP response status code.
        Provided for convenience.
        """
        return STATUS_CODE_TEXT.get(self.status, '')

    def __str__(self):
        """HTTP headers only."""
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self._headers.values()]) + '\n'

    def _convert_to_ascii(self, *values):
        """Converts all values to ascii strings."""
        for value in values:
            if isinstance(value, unicode):
                try:
                    value = value.encode('us-ascii')
                except UnicodeError, e:
                    e.reason += ', HTTP response headers must be in US-ASCII format'
                    raise
            else:
                value = str(value)
            if '\n' in value or '\r' in value:
                raise BadHeaderError("Header values can't contain newlines (got %r)" % (value))
            yield value

    def __setitem__(self, header, value):
        header, value = self._convert_to_ascii(header, value)
        self._headers[header.lower()] = (header, value)

    def __delitem__(self, header):
        try:
            del self._headers[header.lower()]
        except KeyError:
            pass

    def __getitem__(self, header):
        return self._headers[header.lower()][1]

    def has_header(self, header):
        """Case-insensitive check for a header."""
        return self._headers.has_key(header.lower())

    __contains__ = has_header

    def items(self):
        return self._headers.values()

    def get(self, header, alternate):
        return self._headers.get(header.lower(), (None, alternate))[1]

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/',
                   domain=None, secure=False, httponly=False):
        """
        Sets a cookie.

        ``expires`` can be a string in the correct format or a
        ``datetime.datetime`` object in UTC. If ``expires`` is a datetime
        object then ``max_age`` will be calculated.
        """
        self.cookies[key] = value
        if expires is not None:
            if isinstance(expires, datetime.datetime):
                delta = expires - expires.utcnow()
                # Add one second so the date matches exactly (a fraction of
                # time gets lost between converting to a timedelta and
                # then the date string).
                delta = delta + datetime.timedelta(seconds=1)
                # Just set max_age - the max_age logic will set expires.
                expires = None
                max_age = max(0, delta.days * 86400 + delta.seconds)
            else:
                self.cookies[key]['expires'] = expires
        if max_age is not None:
            self.cookies[key]['max-age'] = max_age
            # IE requires expires, so set it if hasn't been already.
            if not expires:
                self.cookies[key]['expires'] = cookie_date(time.time() +
                                                           max_age)
        if path is not None:
            self.cookies[key]['path'] = path
        if domain is not None:
            self.cookies[key]['domain'] = domain
        if secure:
            self.cookies[key]['secure'] = True
        if httponly:
            self.cookies[key]['httponly'] = True

    def delete_cookie(self, key, path='/', domain=None):
        self.set_cookie(key, max_age=0, path=path, domain=domain,
                        expires='Thu, 01-Jan-1970 00:00:00 GMT')

# TODO: remove raw_content/cleaned_content and just use content?
class Response(HttpHeaders):
    """
    An HttpResponse that may include content that hasn't yet been serialized.
    """

    def __init__(self, content=None, status=None, headers=None):
        print "RESPONSE INIT"
        super(Response, self).__init__(status=status, headers=headers)
        #self.media_type = None
        self.has_content_body = content is not None
        self.raw_content = content

    def __str__(self):
        """Full HTTP message, including headers."""
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self._headers.values()]) \
            + '\n\n' + unicode(self.content)

    def _get_content(self):
        return self.raw_content

    def _set_content(self, content):
        self.has_content_body = content is not None
        self.raw_content = content

    content = property(_get_content, _set_content)

class ErrorResponse(Response):
    """
    Errors along with a status code, headers, and cookies
    """

    def __init__(self, message="", messages=None, errors=None, status=httplib.BAD_REQUEST, headers=None, traceback=False):
        print "ERRORRESPONSE INIT"
        super(ErrorResponse, self).__init__(content=None, status=status, headers=headers)
        
        import sys
        
        if traceback:
            (type, value, tb) = sys.exc_info()
            
            if type:
                self.traceback = (type, value, tb) 
        
        self.message = message
        self.messages = messages
        self.errors = errors
