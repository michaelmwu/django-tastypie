"""
Django supports parsing the content of an HTTP request, but only for form POST requests.
That behavior is sufficient for dealing with standard HTML forms, but it doesn't map well
to general HTTP requests.

We need a method to be able to:

1.) Determine the parsed content on a request for methods other than POST (eg typically also PUT)

2.) Determine the parsed content on a request for media types other than application/x-www-form-urlencoded
   and multipart/form-data.  (eg also handle multipart/json)
"""

import httplib

from django.http import QueryDict
from django.http.multipartparser import MultiPartParser as DjangoMultiPartParser
from django.http.multipartparser import MultiPartParserError
from django.utils import simplejson as json
from djangorestframework.compat import yaml
from djangorestframework.response import ErrorResponse
from djangorestframework.utils.mediatypes import media_type_matches


__all__ = (
    'BaseParser',
    'JSONParser',
    'PlainTextParser',
    'FormParser',
    'MultiPartParser',
    'YAMLParser',
)


class BaseParser(object):
    """
    All parsers should extend :class:`BaseParser`, specifying a :attr:`media_type` attribute,
    and overriding the :meth:`parse` method.
    """

    media_type = None

    
    def can_handle_request(self, content_type):
        """
        Returns :const:`True` if this parser is able to deal with the given *content_type*.
        
        The default implementation for this function is to check the *content_type*
        argument against the :attr:`media_type` attribute set on the class to see if
        they match.
        
        This may be overridden to provide for other behavior, but typically you'll
        instead want to just set the :attr:`media_type` attribute on the class.
        """
        return media_type_matches(self.media_type, content_type)

    def parse(self, request, stream):
        """
        Given a *stream* to read from, return the deserialized output.
        Should return a 2-tuple of (data, files).
        """
        raise NotImplementedError("BaseParser.parse() Must be overridden to be implemented.")


class JSONParser(BaseParser):
    """
    Parses JSON-serialized data.
    """

    media_type = 'application/json'

    def parse(self, request, stream):
        """
        Returns a 2-tuple of `(data, files)`.

        `data` will be an object which is the parsed content of the response.
        `files` will always be `None`.
        """
        try:
            return (json.load(stream), None)
        except ValueError, exc:
            raise ErrorResponse(httplib.BAD_REQUEST,
                                {'detail': 'JSON parse error - %s' % unicode(exc)})


if yaml:
    class YAMLParser(BaseParser):
        """
        Parses YAML-serialized data.
        """
    
        media_type = 'application/yaml'
    
        def parse(self, request, stream):
            """
            Returns a 2-tuple of `(data, files)`.
    
            `data` will be an object which is the parsed content of the response.
            `files` will always be `None`.
            """
            try:
                return (yaml.safe_load(stream), None)
            except ValueError, exc:
                raise ErrorResponse(httplib.BAD_REQUEST,
                                    {'detail': 'YAML parse error - %s' % unicode(exc)})
else:
    YAMLParser = None

class PlainTextParser(BaseParser):
    """
    Plain text parser.
    """

    media_type = 'text/plain'

    def parse(self, request, stream):
        """
        Returns a 2-tuple of `(data, files)`.
        
        `data` will simply be a string representing the body of the request.
        `files` will always be `None`.
        """
        return (stream.read(), None)


class FormParser(BaseParser):
    """
    Parser for form data.
    """

    media_type = 'application/x-www-form-urlencoded'

    def parse(self, request, stream):
        """
        Returns a 2-tuple of `(data, files)`.
        
        `data` will be a :class:`QueryDict` containing all the form parameters.
        `files` will always be :const:`None`.
        """
        data = QueryDict(stream.read())
        return (data, None)


class MultiPartParser(BaseParser):
    """
    Parser for multipart form data, which may include file data.
    """

    media_type = 'multipart/form-data'

    def parse(self, request, stream):
        """
        Returns a 2-tuple of `(data, files)`.
        
        `data` will be a :class:`QueryDict` containing all the form parameters.
        `files` will be a :class:`QueryDict` containing all the form files.
        """
        upload_handlers = request._get_upload_handlers()
        try:
            django_parser = DjangoMultiPartParser(request.META, stream, upload_handlers)
        except MultiPartParserError, exc:
            raise ErrorResponse(httplib.BAD_REQUEST,
                                {'detail': 'multipart parse error - %s' % unicode(exc)})
        return django_parser.parse()

DEFAULT_PARSERS = ( JSONParser,
                    FormParser,
                    MultiPartParser )

if YAMLParser:
    DEFAULT_PARSERS += ( YAMLParser, )

class DefaultParser(BaseParser):
    """
    Uses the default parsers as specified by DEFAULT_PARSERS to parse a request
    """
    PARSERS = []
    _parsers = {}

    def __init__(self, view):
        """
        Initialize the parser with the ``View`` instance as state,
        in case the parser needs to access any metadata on the :obj:`View` object.
        """
        self.view = view
    
    def can_handle_request(self, content_type):
        """
        Calls 
        """
        for parser in DEFAULT_PARSERS + PARSERS:
            if parser().can_handle_request(content_type):
                _parsers[content_type] = parser
                return True
        
        return False

    def parse(self, request, stream):
        """
        Given a *stream* to read from, return the deserialized output.
        Should return a 2-tuple of (data, files).
        """
        return _parsers[]
