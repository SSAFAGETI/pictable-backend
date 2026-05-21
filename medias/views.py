from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import MediaFile
from django.shortcuts import get_object_or_404
from .serializers import MediaFileSerializer
import os

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def media_upload(request):
    file    = request.FILES.get('file')
    purpose = request.data.get('purpose', 'general')

    if not file:
        return Response({'error': '파일이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # 저장 경로
    upload_dir = os.path.join('media_files', purpose)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.name)
    with open(file_path, 'wb+') as f:
        for chunk in file.chunks():
            f.write(chunk)

    url = f'/media/{purpose}/{file.name}'

    media = MediaFile.objects.create(
        uploader_user = request.user,
        url           = url,
        original_name = file.name,
        mime_type     = file.content_type,
        purpose       = purpose,
        size_bytes    = file.size,
    )

    return Response({'id': media.id, 'url': url}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def media_detail(request, pk):
    media = get_object_or_404(MediaFile, pk=pk)
    serializer = MediaFileSerializer(media)
    return Response(serializer.data)