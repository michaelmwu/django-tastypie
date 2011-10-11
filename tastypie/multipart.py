"""
Multipart uploads for everyone!

@author: Michael Wu
"""

import cgi
import cStringIO

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.http import BadHeaderError
from django.http.multipartparser import *
from django.http.multipartparser import LimitBytes, LazyStream, ChunkIter, Parser, RAW, FILE, FIELD, exhaust
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_unicode
from django.utils.text import unescape_entities
from django.core.files.uploadhandler import StopUpload, SkipFile, StopFutureHandlers

class HTTPAttachment(object):
    def __init__(self, content=None, headers=None):
        # _headers is a mapping of the lower-case name to the original case of
        # the header (required for working with legacy systems) and the header
        # value.  Both the name of the header and its value are ASCII strings.
        self._headers = {}
        
        if headers:
            for header, value in headers.itemitems():
                header, value = self._convert_header(header, value)
                self._headers[header.lower()] = (header, value)
        
        self._charset = settings.DEFAULT_CHARSET
        
        self.has_content_body = content is not None
        self.raw_content = content
        self._file = cStringIO.StringIO(content)
        self.remaining = len(content)

        print "Headers"
        print headers
 
    def __str__(self):
        """HTTP attachment headers only."""
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self._headers.values()]) \
            + '\n\n' + unicode(self.content)
            
    def _convert_header(self, *values):
        """
        Converts all values to ascii strings and replace dashes with underscores
        to reflect Django's META attribute
        """
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
            value.replace('-', '_')
            yield value

    def __setitem__(self, header, value):
        header, value = self._convert_header(header, value)
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
    
    @property
    def META(self):
        return self._headers

    def _get_content(self):
        return self.raw_content

    def _set_content(self, content):
        self.has_content_body = content is not None
        self.raw_content = content
        self._file = cStringIO.StringIO(content)
        self.remaining = len(content)

    content = property(_get_content, _set_content)
    
    def read(self, num_bytes=None):
        """
        Read data from the attachment.
        """
        if num_bytes is None:
            num_bytes = self.remaining
        else:
            num_bytes = min(num_bytes, self.remaining)
        self.remaining -= num_bytes
        
        return self._file.read(num_bytes)

class MultiPartMixedParser(MultiPartParser):
    def parse(self):
        """
        Parse the POST data and break it into a FILES MultiValueDict, a POST
        MultiValueDict, and a DATA array for attachments

        Returns a tuple containing the DATA, POST and FILES dictionary,
        respectively.
        """
        # We have to import QueryDict down here to avoid a circular import.
        from django.http import QueryDict

        encoding = self._encoding
        handlers = self._upload_handlers
        
        data = self._input_data.read()
        import cStringIO
        self._input_data = cStringIO.StringIO(data) 

        limited_input_data = LimitBytes(self._input_data, self._content_length)
        

        # See if the handler will want to take care of the parsing.
        # This allows overriding everything if somebody wants it.
        for handler in handlers:
            result = handler.handle_raw_input(limited_input_data,
                                              self._meta,
                                              self._content_length,
                                              self._boundary,
                                              encoding)
            if result is not None:
                return result[0], result[1]

        # Create the data structures to be used later.
        self._data = []
        self._post = QueryDict('', mutable=True)
        self._files = MultiValueDict()

        # Instantiate the parser and stream:
        stream = LazyStream(ChunkIter(limited_input_data, self._chunk_size))

        # Whether or not to signal a file-completion at the beginning of the loop.
        old_field_name = None
        counters = [0] * len(handlers)

        try:
            for item_type, meta_data, field_stream in Parser(stream, self._boundary):
                print "ITEM"
                print item_type
                print meta_data
                if old_field_name:
                    # We run this at the beginning of the next loop
                    # since we cannot be sure a file is complete until
                    # we hit the next boundary/part of the multipart content.
                    self.handle_file_complete(old_field_name, counters)
                    old_field_name = None

                try:
                    disposition = meta_data['content-disposition'][1]
                    field_name = disposition['name'].strip()
                except (KeyError, IndexError, AttributeError):
                    field_name = None

                transfer_encoding = meta_data.get('content-transfer-encoding')
                
                if field_name:
                    field_name = force_unicode(field_name, encoding, errors='replace')

                if item_type == FIELD:
                    if field_name is None:
                        """
                        Add to DATA array
                        """
                        if transfer_encoding == 'base64':
                            raw_data = field_stream.read()
                            try:
                                data = str(raw_data).decode('base64')
                            except:
                                data = raw_data
                        else:
                            data = field_stream.read()
                        
                        # Provide the meta data so we can figure out what it was later
                        wrapped_data = HTTPAttachment(data, meta_data)
                        
                        self._data.append(wrapped_data)
                        continue
                    
                    # This is a post field, we can just set it in the post
                    if transfer_encoding == 'base64':
                        raw_data = field_stream.read()
                        try:
                            data = str(raw_data).decode('base64')
                        except:
                            data = raw_data
                    else:
                        data = field_stream.read()

                    self._post.appendlist(field_name,
                                          force_unicode(data, encoding, errors='replace'))
                elif item_type == FILE:
                    if field_name is None:
                        continue
                    
                    # This is a file, use the handler...
                    file_name = disposition.get('filename')
                    if not file_name:
                        continue
                    file_name = force_unicode(file_name, encoding, errors='replace')
                    file_name = self.IE_sanitize(unescape_entities(file_name))

                    content_type = meta_data.get('content-type', ('',))[0].strip()
                    try:
                        charset = meta_data.get('content-type', (0,{}))[1].get('charset', None)
                    except:
                        charset = None

                    try:
                        content_length = int(meta_data.get('content-length')[0])
                    except (IndexError, TypeError, ValueError):
                        content_length = None

                    counters = [0] * len(handlers)
                    try:
                        for handler in handlers:
                            try:
                                handler.new_file(field_name, file_name,
                                                 content_type, content_length,
                                                 charset)
                            except StopFutureHandlers:
                                break

                        for chunk in field_stream:
                            if transfer_encoding == 'base64':
                                # We only special-case base64 transfer encoding
                                try:
                                    chunk = str(chunk).decode('base64')
                                except Exception, e:
                                    # Since this is only a chunk, any error is an unfixable error.
                                    raise MultiPartParserError("Could not decode base64 data: %r" % e)

                            for i, handler in enumerate(handlers):
                                chunk_length = len(chunk)
                                chunk = handler.receive_data_chunk(chunk,
                                                                   counters[i])
                                counters[i] += chunk_length
                                if chunk is None:
                                    # If the chunk received by the handler is None, then don't continue.
                                    break

                    except SkipFile, e:
                        # Just use up the rest of this file...
                        exhaust(field_stream)
                    else:
                        # Handle file upload completions on next iteration.
                        old_field_name = field_name
                else:
                    # If this is neither a FIELD or a FILE, add it to the DATA array
                    if transfer_encoding == 'base64':
                        raw_data = field_stream.read()
                        try:
                            data = str(raw_data).decode('base64')
                        except:
                            data = raw_data
                    else:
                        data = field_stream.read()
                        
                    data = data.trim()
                    
                    # Provide the meta data so we can figure out what it was later
                    wrapped_data = HTTPAttachment(data, meta_data)
                    
                    self._data.append(wrapped_data)
        except StopUpload, e:
            if not e.connection_reset:
                exhaust(limited_input_data)
        else:
            # Make sure that the request data is all fed
            exhaust(limited_input_data)

        # Signal that the upload has completed.
        for handler in handlers:
            retval = handler.upload_complete()
            if retval:
                break

        if len(self._data) == 0:
            data = None
        elif len(self._data) == 1:
            data = self._data[0]
        else:
            data = self._data 

        return data, self._post, self._files