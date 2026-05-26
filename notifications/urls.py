from django.urls import path
from .views import register_fcm_token

urlpatterns = [
    path(
        'register-token/',
        register_fcm_token,
        name='register_token',
    ),
]