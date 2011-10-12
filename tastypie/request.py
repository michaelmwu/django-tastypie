"""
Monkey patches standard Django HTTP Requests to handle multipart uploads

@author: Michael Wu
"""

import cStringIO
from pprint import pformat
import sys

from django.http import HttpRequest, QueryDict, MultiValueDict, ImmutableList
from tastypie.multipart import MultiPartMixedParser
from tastypie.utils.mime import media_type_matches

class TastypieHTTPRequest(HttpRequest):
    def __init__(self, *args, **kwargs):
        super(TastypieHTTPRequest, self).__init__(*args, **kwargs)
        self.upgrade()
    
    def __upgrade__(self):
        """
        Init when monkey patching classes
        """
        pass

    @property
    def content_type(self):
        """
        Returns the content type header.

        This should be used instead of ``request.META.get('HTTP_CONTENT_TYPE')``,
        as it allows the content type to be overridden by using a hidden form
        field on a form POST request.
        """
        if not hasattr(self, '_content_type'):
            self._load_content_type()
        return self._content_type

    @property
    def POST(self):
        """
        Parses the request body and returns the form data.
        """
        if not hasattr(self, '_form'):
            self._load_data_and_files()
        return self._form
    
    @property
    def FORM(self):
        """
        Parses the request body and returns the form data.
        """
        if not hasattr(self, '_form'):
            self._load_data_and_files()
        return self._form

    @property
    def DATA(self):
        """
        Parses the request body and returns the data. For multipart requests,
        will come back as an array???

        Similar to ``request.POST``, except that it handles arbitrary parsers,
        and also works on methods other than POST (eg PUT).
        """
        if not hasattr(self, '_data'):
            self._load_data_and_files()
        return self._data


    @property
    def FILES(self):
        """
        Parses the request body and returns the files.
        Similar to ``request.FILES``, except that it handles arbitrary parsers,
        and also works on methods other than POST (eg PUT).
        """
        if not hasattr(self, '_files'):
            self._load_data_and_files()
        return self._files

    def _load_content_type(self):
        """
        Set the content_type
        """
        self._content_type = self.META.get('HTTP_CONTENT_TYPE', self.META.get('CONTENT_TYPE', ''))

    def _get_stream(self):
        """
        Returns an object that may be used to stream the request content.
        """
        request = self.request

        try:
            content_length = int(request.META.get('CONTENT_LENGTH', request.META.get('HTTP_CONTENT_LENGTH')))
        except (ValueError, TypeError):
            content_length = 0

        # TODO: Add 1.3's LimitedStream to compat and use that.
        # NOTE: Currently only supports parsing request body as a stream with 1.3
        if content_length == 0:
            return None
        elif hasattr(request, 'read'):
             return request
        return cStringIO.StringIO(request.raw_post_data)

    def _mark_post_parse_error(self):
        self._data = []
        self._form = QueryDict('')
        self._files = MultiValueDict()
        self._post_parse_error = True

    def parse_file_upload(self, META, post_data):
        """Returns a tuple of (POST QueryDict, FILES MultiValueDict)."""
        self.upload_handlers = ImmutableList(
            self.upload_handlers,
            warning = "You cannot alter upload handlers after the upload has been processed."
        )
        parser = MultiPartMixedParser(META, post_data, self.upload_handlers, self.encoding)
        return parser.parse()

    def _load_data_and_files(self):
        """
        Parse the request content into self.DATA and self.FILES.
        """
        if not hasattr(self, '_content_type'):
            self._load_content_type()
            
        # Populates self._post and self._files
        if self._read_started:
            self._mark_post_parse_error()
            return

        if self.META.get('CONTENT_TYPE', '').startswith('multipart'):
            self._raw_post_data = ''
            try:
                print "parsing file upload"
                self._data, self._form, self._files = self.parse_file_upload(self.META, self)
                print "parsed!"
                print self._data
                print self._form
                print self._files
            except Exception as e:
                # An error occured while parsing POST data.  Since when
                # formatting the error the request handler might access
                # self.POST, set self._post and self._file to prevent
                # attempts to parse POST data again.
                # Mark that an error occured.  This allows self.__repr__ to
                # be explicit about it instead of simply representing an
                # empty POST
                print "POST PARSE ERROR???"
                self._mark_post_parse_error()
                print e
                raise e
        elif media_type_matches(self.META.get('CONTENT_TYPE', ''), 'application/x-www-form-urlencoded'):
            self._data, self._form, self._files = self, QueryDict(self.raw_post_data, self._encoding), MultiValueDict()
            print self._form
        else:
            self._data, self._form, self._files = self, QueryDict(''), MultiValueDict()
    
    _load_post_and_files = _load_data_and_files
    
    def __repr__(self):
        # Since this is called as part of error handling, we need to be very
        # robust against potentially malformed input.
        try:
            get = pformat(self.GET)
        except:
            get = '<could not parse>'
        if self._post_parse_error:
            post = '<could not parse>'
        else:
            try:
                post = pformat(self.POST)
            except:
                post = '<could not parse>'
        try:
            cookies = pformat(self.COOKIES)
        except:
            cookies = '<could not parse>'
        try:
            meta = pformat(self.META)
        except:
            meta = '<could not parse>'
        return '<TastypieHttpRequest\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (get, post, cookies, meta)
