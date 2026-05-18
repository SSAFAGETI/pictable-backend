from rest_framework.decorators import api_view
from rest_framework.response import Response
from recipes.models import Recipe
from recipes.serializers import RecipeSerializer


@api_view(['GET'])
def index(request):
    # 오늘의 추천
    recommended = Recipe.objects.filter(is_public=True).order_by('-created_at').first()

    # 인기 레시피
    popular = Recipe.objects.filter(is_public=True).order_by('-like_count')[:4]

    # 최근 올라온
    recent = Recipe.objects.filter(is_public=True).order_by('-created_at')[:6]

    return Response({
        'recommended' : RecipeSerializer(recommended).data if recommended else None,
        'popular' : RecipeSerializer(popular, many=True).data,
        'recent' : RecipeSerializer(recent, many=True).data,
    })