from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Recipe, RecipeLike
from .serializers import RecipeSerializer


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
    return Response({'liked': True, 'like_count': recipe.like_count}, status=status.HTTP_201_CREATED)