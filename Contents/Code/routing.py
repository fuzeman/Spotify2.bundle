from settings import PREFIX

import base64
import cerealizer
import urllib


def safe_encode(string):
    return base64.b64encode(string).replace('/','@').replace('+','*').replace('=','_')


def pack(obj):
    serialized_obj = cerealizer.dumps(obj)
    encoded_string = safe_encode(serialized_obj)
    return urllib.quote(encoded_string)


def route_path(path, *args, **kwargs):
    result = '%s/%s%s' % (
        PREFIX,
        path,

        ('/' + ('/'.join([
            str(x) for x in args
        ]))) if args else ''
    )

    if kwargs:
        result += '?' + urllib.urlencode(kwargs)

    return result


def function_path(name, ext=None, **kwargs):
    return '%s/:/function/%s%s?%s' % (
        PREFIX,
        name,
        ('.%s' % ext) if ext else '',

        urllib.urlencode({
            'function_args': pack(kwargs)
        })
    )
