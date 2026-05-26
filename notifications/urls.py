from django.urls import path
from .views import register_fcm_token, test_notification

urlpatterns = [
    path(
        'register-token/',
        register_fcm_token,
        name='register_token',
    ),
    path('test-notification/', test_notification, name='test_notification'),

]