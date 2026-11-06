import os
import traceback
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import JsonResponse
from django.views.static import serve
from django.db import connection
from movies.views import payment_webhook, admin_dashboard

def health_check(request):
    db_info = {}
    try:
        from movies.models import Movie
        db_info['movies_count'] = Movie.objects.count()
        db_info['status'] = 'ok'
    except Exception as e:
        db_info['status'] = 'error'
        db_info['error'] = str(e)
        db_info['traceback'] = traceback.format_exc()
    
    db_info['database_engine'] = connection.settings_dict.get('ENGINE')
    db_info['database_name'] = str(connection.settings_dict.get('NAME'))
    db_info['database_url_present'] = bool(os.environ.get('DATABASE_URL'))
    db_info['vercel_env'] = bool(os.environ.get('VERCEL'))
    return JsonResponse(db_info)

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/dashboard/', admin_dashboard, name='root_admin_dashboard'),
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', include('users.urls')),
    path('movies/', include('movies.urls')),
    path('payment/webhook/', payment_webhook, name='root_payment_webhook'),
    # Serve user/catalog media files (posters, banners) in both development & production
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
