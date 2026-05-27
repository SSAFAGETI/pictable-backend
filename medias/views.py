from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import MediaFile, IngredientDetectionJob
from django.shortcuts import get_object_or_404
from .serializers import MediaFileSerializer
from .tasks import run_ingredient_detection
import uuid
import os

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def media_upload(request):
    file    = request.FILES.get('file')
    purpose = request.data.get('purpose', 'general')

    if not file:
        return Response({'error': '파일이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    ext = os.path.splitext(file.name)[1]
    safe_name = f"{uuid.uuid4().hex}{ext}"

    url = f'/media/{purpose}/{safe_name}'

    media = MediaFile.objects.create(
        uploader_user = request.user,
        url           = url,
        original_name = file.name,
        mime_type     = file.content_type,
        purpose       = purpose,
        size_bytes    = file.size,
    )
    
    response_data = {'id': media.id, 'url': url}

    # AI 재료 인식일 때만 detection 실행
    if purpose == 'ingredient_detection':
        job = IngredientDetectionJob.objects.create(
            user       = request.user,
            media_file = media,
            status     = 'pending',
        )
        run_ingredient_detection(job.id, file)
        response_data['detection_job_id'] = job.id

    return Response(response_data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def media_detail(request, pk):
    media = get_object_or_404(MediaFile, pk=pk)
    serializer = MediaFileSerializer(media)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detection_result(request, job_id):
    job = get_object_or_404(IngredientDetectionJob, id=job_id, user=request.user)
    items = job.items.all()
    return Response({
        'status': job.status,
        'items': [
            {'name': item.detected_name} for item in items
        ]
    })