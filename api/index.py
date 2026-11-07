import os
import sys

# Ensure root directory is on Python module search path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PickMyShow.wsgi import app as django_app

def app(environ, start_response):
    # Vercel Serverless Function WSGI Wrapper
    # Ensure PATH_INFO reflects the actual requested client route
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
