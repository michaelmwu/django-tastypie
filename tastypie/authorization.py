from django.db.models import Q

class Authorization(object):
    """
    A base class that provides no permissions checking.
    """
    def __get__(self, instance, owner):
        """
        Makes ``Authorization`` a descriptor of ``ResourceOptions`` and creates
        a reference to the ``ResourceOptions`` object that may be used by
        methods of ``Authorization``.
        """
        self.resource_meta = instance
        return self

    def is_authorized(self, request, object=None):
        """
        Checks if the user is authorized to perform the request. If ``object``
        is provided, it can do additional row-level checks.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        return True


class ReadOnlyAuthorization(Authorization):
    """
    Default Authentication class for ``Resource`` objects.

    Only allows GET requests.
    """

    def get_limits(self, request, _and, _or):
        return self.is_authorized(request) is True 

    def is_authorized(self, request, object=None):
        """
        Allow any ``GET`` request.
        """
        if request.method == 'GET':
            return True
        else:
            return None

class OpenAuthorization(Authorization):
    """
    Default Authentication class for ``Resource`` objects.

    Only allows GET requests.
    """

    def get_limits(self, request, _and, _or):
        return True 

    def is_authorized(self, request, object=None):
        """
        Allow anything.
        """
        return True

class DjangoAuthorization(Authorization):
    """
    Uses permission checking from ``django.contrib.auth`` to map ``POST``,
    ``PUT``, and ``DELETE`` to their equivalent django auth permissions.
    
    Custom permissions can be specified by providing a permission_codes
    dictionary. This dictionary updates the default dictionary.
    
    Permission codes format is a dict with items:
        'METHOD': '%(app)s.ACTION_%(object)s'
                  None to delete the default action
    """
    # GET allowed by default
    permission_codes = {
        'POST': '%(app)s.add_%(object)s',
        'PUT': '%(app)s.change_%(object)s',
        'DELETE': '%(app)s.delete_%(object)s',
    }
    
    def __init__(self, permission_codes=None):
        # Update default permission codes
        if permission_codes:
            self.permission_codes.update(permission_codes)
        
        # Get rid of None or True values
        for key, value in self.permission_codes.items():
            if value is None or value is True:
                del permission_codes[key]
    
    def get_limits(self, request, _and, _or):
        return self.is_authorized(self, request) is True
    
    def is_authorized(self, request, object=None):
        # cannot map request method to permission code name, so pass through
        if request.method not in self.permission_codes:
            return None

        klass = self.resource_meta.object_class

        # cannot check permissions if we don't know the model
        if not klass:
            return None

        permission_code = self.permission_codes[request.method] % {
            'app': klass._meta.app_label,
            'object': klass._meta.module_name}

        # user must be logged in to check permissions
        # authentication backend must set request.user
        if not hasattr(request, 'user'):
            return False

        return request.user.has_perm(permission_code)

class OwnerDjangoAuthorization(DjangoAuthorization):
    def get_limits(self, request, _and, _or):
        # Pass through GET
        if request.method == 'GET':
            return None

        klass = self.resource_meta.object_class

        # cannot check permissions if we don't know the model
        if not klass:
            return None
        
        meta = klass.meta
        owner_field = getattr(meta, 'owner_field', 'user')
        
        # user must be logged in to check permissions
        # authentication backend must set request.user
        if not hasattr(request, 'user'):
            return None
        
        kwargs = { owner_field: request.user }
        
        return None, Q(*kwargs)
        
    """
    Uses permission checking from ``django.contrib.auth`` to map ``POST``,
    ``PUT``, and ``DELETE`` to their equivalent django auth permissions.
    """
    def is_authorized(self, request, object=None):
        # Pass through if no object is received
        if not object:
            return None
        
        # Pass through GET
        if request.method == 'GET':
            return None

        klass = self.resource_meta.object_class

        # cannot check permissions if we don't know the model
        if not klass:
            return None
        
        meta = klass.meta
        owner_field = getattr(meta, 'owner_field', 'user')

        owner = getattr(object, owner_field, None)

        if not owner:
            return None

        # user must be logged in to check permissions
        # authentication backend must set request.user
        if not hasattr(request, 'user'):
            return None

        return request.user.id == owner.id
