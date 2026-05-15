from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from recipes.models import Recipe, Tag
from recipes.serializers import RecipeSerializer, TagSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def recipe_feed(request):
    queryset = Recipe.objects.filter(is_public=True) \
                             .select_related('author', 'thumbnail_media') \
                             .prefetch_related('ingredients', 'steps', 'tags')

    # 검색
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(title__icontains=search)

    # 태그 필터
    tag = request.query_params.get('tag')
    if tag:
        queryset = queryset.filter(tags__name=tag)

    # 정렬
    sort = request.query_params.get('sort', 'latest')
    if sort == 'popular':
        queryset = queryset.order_by('-like_count')
    elif sort == 'liked':
        queryset = queryset.order_by('-like_count')
    else:  # latest
        queryset = queryset.order_by('-created_at')

    serializer = RecipeSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def tag_list(request):
    if request.method == 'GET':
        tags = Tag.objects.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = TagSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)