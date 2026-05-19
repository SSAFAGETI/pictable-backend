from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer

# 알림 목록 조회
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = Notification.objects.filter(receiver=request.user)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

# 알림 읽음 처리
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def notification_read(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, receiver=request.user)
    except Notification.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    return Response({'is_read': True})

# 전체 읽음 처리
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def notification_read_all(request):
    Notification.objects.filter(receiver=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    return Response({'message': '전체 읽음 처리 완료'})