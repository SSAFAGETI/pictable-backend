from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Recipe, RecipeLike, RecipeSave, Comment, RecipeIngredient
from .serializers import RecipeSerializer, CommentSerializer
from notifications.utils import notify_welcome, notify_like, notify_comment, notify_reply
from django.db import connection

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

def normalize_ingredients(raw_ingredients: list) -> list:
    if not raw_ingredients:
        return []

    placeholders = ','.join(['%s'] * len(raw_ingredients))
    sql = f"""
        SELECT alias_name, ingredient_name
        FROM ingredient_aliases
        WHERE alias_name IN ({placeholders})
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, raw_ingredients)
        rows = cursor.fetchall()

    alias_map = {row[0]: row[1] for row in rows}

    normalized = []
    for name in raw_ingredients:
        normalized.append(alias_map.get(name, name))

    return list(set(normalized))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommend_recipes(request):
    raw_ingredients = request.query_params.get('ingredients', '')
    
    if not raw_ingredients:
        return Response(
            {'detail': 'ingredients를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # "돼지고기,마늘" → ["돼지고기", "마늘"]
    ingredient_list = [i.strip() for i in raw_ingredients.split(',') if i.strip()]
    
    if len(ingredient_list) > 50:
        return Response(
            {'detail': '재료는 최대 50개까지 입력 가능합니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        normalized = normalize_ingredients(ingredient_list)

        can_make, almost = get_recommendations(normalized)

        return Response({
            'input_ingredients': normalized,
            'can_make': can_make,
            'almost': almost,
        })

    except Exception as e:
        return Response(
            {'detail': '추천 중 오류가 발생했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
    
def get_recommendations(normalized_ingredients: list):
    if not normalized_ingredients:
        return [], []

    placeholders = ','.join(['%s'] * len(normalized_ingredients))

    sql = f"""
        WITH recipe_stats AS (
            SELECT
                r.id                AS recipe_id,
                r.title,
                r.description,
                r.cook_time,
                r.servings,
                r.like_count,
                r.thumbnail_media_id,
                COUNT(ri.id)        AS total_count,
                COUNT(
                    CASE
                        WHEN EXISTS (
                            SELECT 1 FROM ingredient_aliases ia
                            WHERE ia.alias_name = ri.name
                              AND ia.ingredient_name IN ({placeholders})
                        )
                        OR ri.name IN ({placeholders})
                        THEN 1
                    END
                )                   AS match_count,
                ARRAY_AGG(ri.name) FILTER (WHERE
                    NOT (
                        EXISTS (
                            SELECT 1 FROM ingredient_aliases ia
                            WHERE ia.alias_name = ri.name
                              AND ia.ingredient_name IN ({placeholders})
                        )
                        OR ri.name IN ({placeholders})
                    )
                )                   AS missing_ingredients
            FROM recipes_recipe r
            JOIN recipes_recipeingredient ri ON ri.recipe_id = r.id
            WHERE r.is_public = true
            GROUP BY r.id, r.title, r.description, r.cook_time, r.servings, r.like_count, r.thumbnail_media_id
        )
        SELECT
            recipe_id,
            title,
            description,
            cook_time,
            servings,
            like_count,
            thumbnail_media_id,
            total_count,
            match_count,
            ROUND(match_count::numeric / NULLIF(total_count, 0), 4) AS match_rate,
            COALESCE(missing_ingredients, ARRAY[]::text[])           AS missing_ingredients,
            (total_count - match_count)                              AS missing_count
        FROM recipe_stats
        WHERE match_count > 0
        ORDER BY match_rate DESC, like_count DESC
        LIMIT 100
    """

    params = normalized_ingredients * 4

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    can_make = []
    almost = []

    for row in rows:
        (recipe_id, title, description, cook_time, servings,
         like_count, thumbnail_media_id, total_count, match_count,
         match_rate, missing_ingredients, missing_count) = row

        item = {
            'recipe_id': recipe_id,
            'title': title,
            'description': description,
            'cook_time': cook_time,
            'servings': servings,
            'like_count': like_count,
            'thumbnail_media_id': thumbnail_media_id,
            'match_rate': float(match_rate) if match_rate else 0.0,
            'missing_ingredients': [m for m in missing_ingredients if m] if missing_ingredients else [],
            'missing_count': missing_count,
        }

        if missing_count == 0:
            can_make.append(item)
        elif missing_count <= 2:
            almost.append(item)

    return can_make, almost