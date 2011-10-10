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

from StringIO import StringIO
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import QueryDict
from django.http.multipartparser import MultiPartParser as DjangoMultiPartParser
from django.http.multipartparser import MultiPartParserError
from django.utils import simplejson as json

try:
    import lxml
    from lxml.etree import parse as parse_xml
    from lxml.etree import Element, tostring
except ImportError:
    lxml = None
try:
    import yaml
    from django.core.serializers import pyyaml
except ImportError:
    yaml = None
try:
    import biplist
except ImportError:
    biplist = None

from tastypie.response import ErrorResponse
from tastypie.utils.mime import media_type_matches


__all__ = (
    'BaseParser',
    'JSONParser',
    'PlainTextParser',
    'FormParser',
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

    def parse(self, content, content_type=None, request=None):
        """
        Given a *stream* or *string*, return the deserialized output.
        Should return the deserialized data.
        """
        raise NotImplementedError("BaseParser.parse() Must be overridden to be implemented.")


class JSONParser(BaseParser):
    """
    Parses JSON-serialized data.
    """

    media_type = 'application/json'

    def parse(self, content, content_type=None, request=None):
        """
        Returns deserialized json content.
        
        `data` will be an object which is the parsed content of the response.
        """
        try:
            if getattr(content, 'read', None):
                return json.load(content)
            else:
                return json.loads(content)
        except ValueError, exc:
            raise ErrorResponse(httplib.BAD_REQUEST,
                                {'detail': 'JSON parse error - %s' % unicode(exc)})

if yaml:
    class YAMLParser(BaseParser):
        """
        Parses YAML-serialized data.
        """
    
        media_type = 'application/yaml'
    
        def parse(self, content, content_type=None, request=None):
            """
            Returns deserialized YAML content
    
            `data` will be an object which is the parsed content of the response.
            """
            try:
                return yaml.safe_load(content)
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

    def parse(self, content, content_type=None, request=None):
        """
        Returns the plain text content.
        
        `data` will simply be a string representing the body of the request.
        """
        if getattr(content, 'read', None):
            content = content.read()
        
        return content


class FormParser(BaseParser):
    """
    Parser for form data.
    """

    media_type = 'application/x-www-form-urlencoded'
    multipart_media_type = 'multipart/form-data'

    def can_handle_request(self, content_type):
        return media_type_matches(self.media_type, content_type) or media_type_matches(self.multipart_media_type, content_type)

    def parse(self, content, content_type=None, request=None):
        """
        Returns form, parsed into an object with keys
        
        `data` will be a :class:`QueryDict` containing all the form parameters.
        """
        print "form parsing"
        
        if self.can_handle_request(request.META.get('CONTENT_TYPE', '')):
            print "can handle"
            print request.POST
            return request.POST
        else:
            print "nope"
            return QueryDict(content, request._encoding)

if lxml:
    class XMLParser(BaseParser):
        """
        Not the smartest deserializer on the planet. At the request level,
        it first tries to output the deserialized subelement called "object"
        or "objects" and falls back to deserializing based on hinted types in
        the XML element attribute "type".
        """
        
        media_type = 'application/xml'
        
        def parse(self, content, content_type=None, request=None):
            if isinstance(content, basestring):
                content = StringIO(content)
            
            data = parse_xml(content).getroot()
            
            if data.tag == 'request':
                # if "object" or "objects" exists, return deserialized forms.
                elements = data.getchildren()
                for element in elements:
                    if element.tag in ('object', 'objects'):
                        return self.from_etree(element)
                return dict((element.tag, self.from_etree(element)) for element in elements)
            elif data.tag == 'object' or data.get('type') == 'hash':
                return dict((element.tag, self.from_etree(element)) for element in data.getchildren())
            elif data.tag == 'objects' or data.get('type') == 'list':
                return [self.from_etree(element) for element in data.getchildren()]
            else:
                type_string = data.get('type')
                if type_string in ('string', None):
                    return data.text
                elif type_string == 'integer':
                    return int(data.text)
                elif type_string == 'float':
                    return float(data.text)
                elif type_string == 'boolean':
                    if data.text == 'True':
                        return True
                    else:
                        return False
                else:
                    return None
else:
    XMLParser = None

if biplist:
    class PListParser(BaseParser):
        """
        Given some binary plist data, returns a Python dictionary of the decoded data.
        """
        
        media_type = 'application/x-plist'
        
        def parse(self, content, content_type=None, request=None):            
            return biplist.readPlistFromString(content)
else:
    PListParser = None


DEFAULT_PARSERS = ( JSONParser, )

if YAMLParser:
    DEFAULT_PARSERS += ( YAMLParser, )

if XMLParser:
    DEFAULT_PARSERS += ( YAMLParser, )

if PListParser:
    DEFAULT_PARSERS += ( PListParser, )
    
DEFAULT_PARSERS += ( FormParser, )

