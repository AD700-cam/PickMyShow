import os
import sys
import json

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PickMyShow.wsgi import app as django_app

def app(environ, start_response):
    if 'debug_env=1' in environ.get('QUERY_STRING', ''):
        data = {
            'PATH_INFO': environ.get('PATH_INFO'),
            'SCRIPT_NAME': environ.get('SCRIPT_NAME'),
            'RAW_URI': environ.get('RAW_URI'),
            'REQUEST_URI': environ.get('REQUEST_URI'),
            'keys': {k: str(v) for k, v in environ.items() if k.startswith('HTTP_') or k in ('PATH_INFO', 'SCRIPT_NAME', 'QUERY_STRING')}
        }
        start_response('200 OK', [('Content-Type', 'application/json')])
        return [json.dumps(data, indent=2).encode()]

    path_info = environ.get('PATH_INFO', '')
    if path_info.startswith('/api/index.py') or path_info.startswith('/api'):
        real_path = (
            environ.get('HTTP_X_MATCHED_PATH')
            or environ.get('HTTP_X_VERCEL_FORWARDED_PATH')
            or environ.get('HTTP_X_FORWARDED_PATH')
        )
        if real_path:
            environ['PATH_INFO'] = real_path
        elif path_info in ('/api/index.py', '/api', '/api/index.py/'):
            environ['PATH_INFO'] = '/'
        else:
            stripped = path_info.replace('/api/index.py', '', 1)
            environ['PATH_INFO'] = stripped if stripped.startswith('/') else '/' + stripped

    return django_app(environ, start_response)
