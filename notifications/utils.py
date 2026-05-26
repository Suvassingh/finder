from firebase_admin import messaging
from .models import FCMToken

def send_push_notification(user, title, body, data=None):
    tokens = FCMToken.objects.filter(user=user).values_list('token', flat=True)
    if not tokens:
        return
    for token in tokens:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=token,
        )
        try:
            messaging.send(message)
        except Exception as e:
            print(f"Failed to send to token {token}: {e}")