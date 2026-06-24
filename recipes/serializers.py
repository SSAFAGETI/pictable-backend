from rest_framework import serializers
from .models import Recipe, RecipeStep, RecipeIngredient, RecipeImage, Comment, Tag
from medias.serializers import MediaFileSerializer
from medias.models import MediaFile

class RecipeIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'amount']

class RecipeStepSerializer(serializers.ModelSerializer):
    image = MediaFileSerializer(read_only=True) # ← ID → URL 포함 객체로 변경
    image_id = serializers.PrimaryKeyRelatedField(
        queryset=MediaFile.objects.all(), source='image',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = RecipeStep
        fields = ['id', 'order', 'description', 'image', 'image_id']
        
class RecipeImageSerializer(serializers.ModelSerializer):
    media_file = MediaFileSerializer(read_only=True)

    class Meta:
        model  = RecipeImage
        fields = ['id', 'media_file', 'sort_order']
        
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Tag
        fields = ['id', 'name']

class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True)
    steps       = RecipeStepSerializer(many=True)
    author      = serializers.StringRelatedField(read_only=True)
    tags        = TagSerializer(many=True, read_only=True)
    tag_ids     = serializers.PrimaryKeyRelatedField(many=True, write_only=True, queryset=Tag.objects.all(), source='tags', required=False)
    thumbnail_media = MediaFileSerializer(read_only=True)
    thumbnail_media_id = serializers.PrimaryKeyRelatedField(
        queryset=MediaFile.objects.all(), source='thumbnail_media',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model  = Recipe
        fields = [
            'id', 'author', 'title', 'description',
            'thumbnail_media', 'thumbnail_media_id', 'cook_time', 'servings',
            'is_public', 'ingredients', 'steps',
            'tags', 'tag_ids',
            'like_count', 'save_count', 'comment_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']

    def create(self, validated_data):
        tags_data        = validated_data.pop('tags', []) or []
        ingredients_data = validated_data.pop('ingredients')
        steps_data       = validated_data.pop('steps')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient in ingredients_data:
            RecipeIngredient.objects.create(recipe=recipe, **ingredient)

        for step in steps_data:
            RecipeStep.objects.create(recipe=recipe, **step)

        return recipe

    def update(self, instance, validated_data):
        tags_data        = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', None)
        steps_data       = validated_data.pop('steps', None)

        # Recipe 기본 필드 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 태그 덮어쓰기
        if tags_data is not None:
            instance.tags.set(tags_data)

        # 재료 덮어쓰기
        if ingredients_data is not None:
            instance.ingredients.all().delete()
            for ingredient in ingredients_data:
                RecipeIngredient.objects.create(recipe=instance, **ingredient)

        # 스텝 덮어쓰기
        if steps_data is not None:
            instance.steps.all().delete()
            for step in steps_data:
                RecipeStep.objects.create(recipe=instance, **step)

        return instance
    
class ReplySerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = Comment
        fields = ['id', 'author', 'content', 'created_at', 'updated_at']

class CommentSerializer(serializers.ModelSerializer):
    author  = serializers.StringRelatedField(read_only=True)
    replies = ReplySerializer(many=True, read_only=True)

    class Meta:
        model  = Comment
        fields = ['id', 'author', 'content', 'replies', 'created_at', 'updated_at']