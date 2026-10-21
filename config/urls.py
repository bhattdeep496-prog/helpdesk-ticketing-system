"""
URL configuration for config project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_status(request):
    return JsonResponse({
        'status': 'online',
        'message': 'Helpdesk Ticket System API is running.',
        'endpoints': {
            'admin': '/admin/',
            'login': '/api/login/',
            'logout': '/api/logout/',
            'docs': '/api/docs/',
        }
    })


urlpatterns = [
    # Web UI (login, dashboard, ...). Root '/' login page kholta hai.
    path('', include('accounts.ui_urls')),

    # API status (pehle '/' par tha)
    path('api/status/', api_status, name='api-status'),

    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('tickets.urls')),
]

# Uploaded files (attachments): dev me hamesha, production me sirf SERVE_MEDIA=1 par.
# (Bade production setup me S3 / nginx use karo.)
import os
from django.views.static import serve as _serve_media
from django.urls import re_path

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif os.environ.get('SERVE_MEDIA', '1').lower() in ('1', 'true', 'yes'):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', _serve_media, {'document_root': settings.MEDIA_ROOT}),
    ]

