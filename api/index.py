import os
import sys
from urllib.parse import parse_qs, urlencode

# Ensure root directory is in sys.path so PickMyShow can be imported
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PickMyShow.wsgi import application as django_app

def app(environ, start_response):
    query_string = environ.get('QUERY_STRING', '')
    if 'path=' in query_string:
        params = parse_qs(query_string, keep_blank_values=True)
        paths = params.pop('path', ['/'])
        target_path = paths[0]
        while target_path.startswith('//'):
            target_path = target_path[1:]
        if not target_path.startswith('/'):
            target_path = '/' + target_path
        environ['PATH_INFO'] = target_path
        environ['QUERY_STRING'] = urlencode({k: v[0] if len(v) == 1 else v for k, v in params.items()}, doseq=True)
    elif environ.get('PATH_INFO') == '/api/index':
        environ['PATH_INFO'] = '/'
    
    environ['SCRIPT_NAME'] = ''
    return django_app(environ, start_response)
