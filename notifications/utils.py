import logging
from firebase_admin import messaging
from .models import FCMToken

logger = logging.getLogger(__name__)

def send_push_notification(user, title, body, data=None):
    """
    Send a push notification to all FCM tokens of a given user.
    Returns a dict with counts: {'success': int, 'failed': int}
    """
    tokens = list(FCMToken.objects.filter(user=user).values_list('token', flat=True))
    if not tokens:
        logger.info(f"No FCM tokens found for user {user.email}. Notification not sent.")
        return {'success': 0, 'failed': 0}

    success = 0
    failed = 0
    for token in tokens:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=token,
        )
        try:
            response = messaging.send(message)
            logger.info(f"Notification sent to {user.email} (token: {token[:10]}...): {response}")
            success += 1
        except Exception as e:
            logger.error(f"Failed to send to token {token[:10]}... for user {user.email}: {e}")
            failed += 1

    return {'success': success, 'failed': failed}