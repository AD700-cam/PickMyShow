from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from movies.views import payment_webhook, admin_dashboard

urlpatterns = [
    path('admin/dashboard/', admin_dashboard, name='root_admin_dashboard'),
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', include('users.urls')),
    path('movies/', include('movies.urls')),
    path('payment/webhook/', payment_webhook, name='root_payment_webhook'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
