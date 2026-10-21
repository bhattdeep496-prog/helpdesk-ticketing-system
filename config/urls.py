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

# Development mein uploaded files (attachments) browser mein kholne ke liye
if settings.DEBUG and getattr(settings, 'MEDIA_URL', ''):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

