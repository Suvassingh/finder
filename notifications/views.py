from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import FCMToken

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_fcm_token(request):
    token = request.data.get('token')
    if not token:
        return Response({'error': 'Token required'}, status=400)
    
    FCMToken.objects.update_or_create(user=request.user, defaults={'token': token})
    return Response({'status': 'ok'})