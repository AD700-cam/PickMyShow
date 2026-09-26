from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from movies.views import payment_webhook, admin_dashboard

urlpatterns = [
    path('admin/dashboard/', admin_dashboard, name='root_admin_dashboard'),
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', include('users.urls')),
    path('movies/', include('movies.urls')),
    path('payment/webhook/', payment_webhook, name='root_payment_webhook'),
    # Serve user/catalog media files (posters, banners) in both development & production
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
