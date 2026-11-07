import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PickMyShow.wsgi import app as django_app

def app(environ, start_response):
    if environ.get('HTTP_X_INSPECT') == '1' or 'inspect=1' in environ.get('QUERY_STRING', ''):
        body = f"PATH_INFO: {environ.get('PATH_INFO')}\nSCRIPT_NAME: {environ.get('SCRIPT_NAME')}\nMATCHED: {environ.get('HTTP_X_MATCHED_PATH')}\nRAW_URI: {environ.get('RAW_URI')}\n"
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [body.encode()]

    # Always ensure clean root path for Django
    real_path = environ.get('HTTP_X_MATCHED_PATH') or environ.get('PATH_INFO', '/')
    if real_path.startswith('/api/index.py'):
        real_path = real_path.replace('/api/index.py', '', 1) or '/'
    elif real_path.startswith('/api'):
        real_path = real_path.replace('/api', '', 1) or '/'

    if not real_path.startswith('/'):
        real_path = '/' + real_path

    environ['PATH_INFO'] = real_path
    environ['SCRIPT_NAME'] = ''

    return django_app(environ, start_response)
