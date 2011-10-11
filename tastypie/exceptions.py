import httplib

from django.http import HttpResponse
from response import Response

class TastypieError(Exception):
    """A base exception for other tastypie-related errors."""
    status_code = httplib.INTERNAL_SERVER_ERROR
    
    def __init__(self, msg=None, headers=None, status=None):
        self.headers = headers
        
        if status:
            self.status_code = status
        
        self.message = msg
        
        if msg is not None:
            super(TastypieError, self).__init__(msg)
        else:
            super(TastypieError, self).__init__()

class Unauthorized(TastypieError):
    """
    Raised when the user is unauthorized
    """
    status_code = httplib.UNAUTHORIZED
    
    def __init__(self, msg=None, auth_header=None, headers={}):
        headers = headers or {}
        
        if auth_header:
            headers['WWW-Authenticate'] = auth_header
        
        super(Unauthorized, self).__init__(headers=headers)

class PermissionDenied(TastypieError):
    """
    Raised when the user is denied permission for a resource
    """
    status_code = httplib.FORBIDDEN

class MethodNotAllowed(TastypieError):
    """
    Raised when the user is denied permission for a resource
    """
    status_code = httplib.METHOD_NOT_ALLOWED
    
    def __init__(self, allows, msg=None, headers={}):
        headers['Allow'] = ','.join(map(str.upper, allows))
        
        if not msg:
            msg = 'Allowed methods: ' + ', '.join(map(str.upper, allows))
        
        super(MethodNotAllowed, self).__init__(msg, headers=headers)


class HydrationError(TastypieError):
    """Raised when there is an error hydrating data."""
    pass

class NotRegistered(TastypieError):
    """
    Raised when the requested resource isn't registered with the ``Api`` class.
    """
    pass


class NotFound(TastypieError):
    """
    Raised when the resource/object in question can't be found.
    """
    status_code = httplib.NOT_FOUND

class ApiFieldError(TastypieError):
    """
    Raised when there is a configuration error with a ``ApiField``.
    """
    pass


class UnsupportedFormat(TastypieError):
    """
    Raised when an unsupported serialization format is requested.
    """
    status_code = httplib.NOT_ACCEPTABLE

class BadRequest(TastypieError):
    """
    A generalized exception for indicating incorrect request parameters.
    
    Handled specially in that the message tossed by this exception will be
    presented to the end user.
    """
    status_code = httplib.BAD_REQUEST

class BlueberryFillingFound(TastypieError):
    pass


class InvalidFilterError(BadRequest):
    """
    Raised when the end user attempts to use a filter that has not be
    explicitly allowed.
    """
    pass


class InvalidSortError(TastypieError):
    """
    Raised when the end user attempts to sort on a field that has not be
    explicitly allowed.
    """
    pass


class ImmediateHttpResponse(TastypieError):
    """
    This exception is used to interrupt the flow of processing to immediately
    return a custom HttpResponse.
    
    Common uses include::
    
        * for authentication (like digest/OAuth)
        * for throttling
    
    """
    response = HttpResponse("Nothing provided.")
    
    def __init__(self, response):
        self.response = response

