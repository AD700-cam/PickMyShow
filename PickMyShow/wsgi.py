"""
WSGI config for PickMyShow project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from urllib.parse import parse_qs, urlencode, unquote
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PickMyShow.settings')

raw_application = get_wsgi_application()

def application(environ, start_response):
    query_string = environ.get('QUERY_STRING', '')
    if 'path=' in query_string:
        params = parse_qs(query_string, keep_blank_values=True)
        paths = params.pop('path', ['/'])
        target_path = unquote(paths[0])
        while target_path.startswith('//'):
            target_path = target_path[1:]
        if not target_path.startswith('/'):
            target_path = '/' + target_path
        environ['PATH_INFO'] = target_path
        environ['QUERY_STRING'] = urlencode({k: v[0] if len(v) == 1 else v for k, v in params.items()}, doseq=True)
    elif environ.get('PATH_INFO') == '/api/index':
        environ['PATH_INFO'] = '/'
    
    environ['SCRIPT_NAME'] = ''
    return raw_application(environ, start_response)

app = application
