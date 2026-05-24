from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "service": "Service Finder API",
        "version": "1.0.0",
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', health_check, name='health_check'),

    # Auth
    path('api/accounts/', include('accounts.api_urls')),


    path('api/listings/', include('listings.urls')),

    # Reviews
    path('api/reviews/', include('reviews.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
