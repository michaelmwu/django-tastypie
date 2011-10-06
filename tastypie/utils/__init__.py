from tastypie.utils.dict import dict_strip_unicode_keys
from tastypie.utils.formatting import mk_datetime, format_datetime, format_date, format_time
from tastypie.utils.urls import trailing_slash, tp_url
from tastypie.utils.validate_jsonp import is_valid_jsonp_callback_value

def as_tuple(obj):
    """
    Given an object which may be a list/tuple, another object, or None,
    return that object in list form.

    IE:
    If the object is already a list/tuple just return it.
    If the object is not None, return it in a list with a single element.
    If the object is None return an empty list.
    """
    if obj is None:
        return ()
    elif isinstance(obj, list):
        return tuple(obj)
    elif isinstance(obj, tuple):
        return obj
    return (obj,)
