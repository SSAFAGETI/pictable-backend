from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .serializers import UserMeSerializer
from recipes.models import Recipe, RecipeLike, RecipeSave
from recipes.serializers import RecipeSerializer
from accounts.models import User
from notifications.utils import notify_follow
from pagination import FeedCursorPagination

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == 'GET':
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = UserMeSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_saved_recipes(request):
    # 리스트 변환 제거 → queryset 직접 사용
    queryset = Recipe.objects.filter(
        saves__user=request.user
    ).select_related('author', 'thumbnail_media') \
     .prefetch_related('ingredients', 'steps', 'tags') \
     .order_by('-saves__created_at', '-id')

    paginator = FeedCursorPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = RecipeSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_liked_recipes(request):
    queryset = Recipe.objects.filter(
        likes__user=request.user
    ).select_related('author', 'thumbnail_media') \
     .prefetch_related('ingredients', 'steps', 'tags') \
     .order_by('-likes__created_at', '-id')

    paginator = FeedCursorPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = RecipeSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_recipes(request):
    queryset = Recipe.objects.filter(
        author=request.user
    ).select_related('author', 'thumbnail_media') \
     .prefetch_related('ingredients', 'steps', 'tags') \
     .order_by('-created_at', '-id')

    paginator = FeedCursorPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = RecipeSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subscribe(request, pk):
    target = get_object_or_404(User, pk=pk)

    if target == request.user:
        return Response({'error': '자기 자신을 구독할 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    from accounts.models import UserFollow
    follow, created = UserFollow.objects.get_or_create(
        follower=request.user,
        following=target,
    )

    if not created:
        follow.delete()
        return Response({'subscribed': False})

    notify_follow(actor=request.user, receiver=target)
    return Response({'subscribed': True}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_subscriptions(request):
    from accounts.models import UserFollow
    follows = UserFollow.objects.filter(follower=request.user).select_related('following')
    users = [f.following for f in follows]
    serializer = UserMeSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_subscribers(request):
    from accounts.models import UserFollow
    follows = UserFollow.objects.filter(following=request.user).select_related('follower')
    users = [f.follower for f in follows]
    serializer = UserMeSerializer(users, many=True)
    return Response(serializer.data)