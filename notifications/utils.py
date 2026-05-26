
import logging
from firebase_admin import messaging
from .models import Notification as NotificationModel, FCMToken

logger = logging.getLogger(__name__)

def send_push_notification(user, title, body, data=None):
    # Save to database first
    notif = NotificationModel.objects.create(
        user=user,
        title=title,
        body=body,
        data=data or {}
    )
    
    # Then try to send push
    tokens = list(FCMToken.objects.filter(user=user).values_list('token', flat=True))
    if not tokens:
        logger.info(f"No FCM tokens for {user.email}")
        return {'success': 0, 'failed': 0}

    # Convert data to string values
    string_data = {str(k): str(v) for k, v in (data or {}).items()}

    success = 0
    failed = 0
    for token in tokens:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=string_data,
            token=token,
        )
        try:
            messaging.send(message)
            success += 1
        except Exception as e:
            logger.error(f"FCM send error to {user.email}: {e}")
            failed += 1
    return {'success': success, 'failed': failed}