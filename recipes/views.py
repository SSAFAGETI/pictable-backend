from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Recipe, RecipeLike, RecipeSave, Comment, RecipeIngredient
from .serializers import RecipeSerializer, CommentSerializer
from notifications.utils import notify_welcome, notify_like, notify_comment, notify_reply

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def recipe_list(request):
    if request.method == 'GET':
        recipes = Recipe.objects.select_related('author', 'thumbnail_media') \
                                .prefetch_related('ingredients', 'steps')
        serializer = RecipeSerializer(recipes, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = RecipeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def recipe_detail(request, pk):
    recipe = get_object_or_404(
        Recipe.objects.select_related('author', 'thumbnail_media')
                    .prefetch_related('ingredients', 'steps'),
        pk=pk
    )

    if request.method == 'GET':
        serializer = RecipeSerializer(recipe)
        return Response(serializer.data)

    # 수정/삭제는 작성자만
    if recipe.author != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        serializer = RecipeSerializer(recipe, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recipe_like(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    like, created = RecipeLike.objects.get_or_create(recipe=recipe, user=request.user)

    if not created:
        # 이미 좋아요 있으면 취소
        like.delete()
        recipe.like_count -= 1
        recipe.save()
        return Response({'liked': False, 'like_count': recipe.like_count})

    recipe.like_count += 1
    recipe.save()
    notify_like(actor=request.user, recipe=recipe)
    return Response({'liked': True, 'like_count': recipe.like_count}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recipe_save(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    save, created = RecipeSave.objects.get_or_create(recipe=recipe, user=request.user)

    if not created:
        save.delete()
        recipe.save_count -= 1
        recipe.save()
        return Response({'saved': False, 'save_count': recipe.save_count})

    recipe.save_count += 1
    recipe.save()
    return Response({'saved': True, 'save_count': recipe.save_count}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def ingredient_list(request):
    search = request.query_params.get('search', '')
    ingredients = RecipeIngredient.objects.filter(
        name__icontains=search
    ).values('id', 'name', 'amount').distinct().order_by('name')[:50]

    return Response(list(ingredients))

# 댓글 목록 조회 / 작성
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def comment_list(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == 'GET':
        comments = Comment.objects.filter(
            recipe=recipe,
            parent_comment=None,  # 답글 제외하고 댓글만
            deleted_at=None
        ).prefetch_related('replies')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            comment = serializer.save(author=request.user, recipe=recipe)
            recipe.comment_count += 1
            recipe.save()
            notify_comment(actor=request.user, recipe=recipe, comment=comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 답글 작성
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reply_create(request, pk, comment_pk):
    recipe  = get_object_or_404(Recipe, pk=pk)
    comment = get_object_or_404(Comment, pk=comment_pk, recipe=recipe, parent_comment=None)

    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        reply = serializer.save(author=request.user, recipe=recipe, parent_comment=comment)
        notify_reply(actor=request.user, recipe=recipe, comment=comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 댓글/답글 수정 / 삭제
@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def comment_detail(request, pk, comment_pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    comment = get_object_or_404(Comment, pk=comment_pk, recipe__id=pk, deleted_at=None)

    # 수정/삭제는 작성자만
    if comment.author != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            recipe.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        from django.utils import timezone
        comment.deleted_at = timezone.now()
        comment.save()
        recipe.comment_count -= 1
        recipe.save()
        return Response(status=status.HTTP_204_NO_CONTENT)