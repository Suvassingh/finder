import logging
from firebase_admin import messaging
from .models import FCMToken

logger = logging.getLogger(__name__)

def send_push_notification(user, title, body, data=None):
    tokens = list(FCMToken.objects.filter(user=user).values_list('token', flat=True))
    if not tokens:
        logger.info(f"No FCM tokens found for user {user.email}")
        return {'success': 0, 'failed': 0}

    # Convert all data values to strings
    if data is None:
        data = {}
    string_data = {str(k): str(v) for k, v in data.items()}

    success = 0
    failed = 0
    for token in tokens:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=string_data,          # <-- now all values are strings
            token=token,
        )
        try:
            response = messaging.send(message)
            logger.info(f"Notification sent to {user.email}: {response}")
            success += 1
        except Exception as e:
            logger.error(f"Failed to send to {user.email}: {e}")
            failed += 1

    return {'success': success, 'failed': failed}