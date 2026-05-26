from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.serializers import NotificationSerializer
from notifications.utils import send_push_notification
from .models import FCMToken, Notification

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_fcm_token(request):
    token = request.data.get('token')
    if not token:
        return Response({'error': 'Token required'}, status=400)
    
    FCMToken.objects.update_or_create(user=request.user, defaults={'token': token})
    return Response({'status': 'ok'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_notification(request):
    """
    Send a test push notification to the requesting user.
    Optional: pass 'user_id' in body to send to another user (admin only).
    """
    target_user = request.user
    user_id = request.data.get('user_id')
    if user_id and request.user.is_staff:
        from django.contrib.auth.models import User
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

    title = request.data.get('title', 'Test Notification')
    body = request.data.get('body', 'This is a test push notification from your server.')
    data = request.data.get('data', {})

    result = send_push_notification(target_user, title, body, data)
    return Response({
        'message': f'Notification sent to {target_user.email}',
        'result': result
    })
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    """Get all notifications for the current user, newest first."""
    notifications = request.user.notifications.all()
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a single notification as read."""
    try:
        notif = request.user.notifications.get(id=notification_id)
        notif.is_read = True
        notif.save()
        return Response({'status': 'ok'})
    except Notification.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    """Mark all notifications for the user as read."""
    request.user.notifications.update(is_read=True)
    return Response({'status': 'ok'})