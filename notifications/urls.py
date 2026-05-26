from django.urls import path
from .views import (
    register_fcm_token,
    test_notification,
    list_notifications,
    mark_notification_read,
    mark_all_read,
)

urlpatterns = [
    path('register-token/', register_fcm_token, name='register_token'),
    path('test-notification/', test_notification, name='test_notification'),
    path('list/', list_notifications, name='list_notifications'),
    path('mark-read/<int:notification_id>/', mark_notification_read, name='mark_read'),
    path('mark-all-read/', mark_all_read, name='mark_all_read'),
]