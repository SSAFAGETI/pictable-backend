from rest_framework import serializers
from .models import Recipe, RecipeStep, RecipeIngredient


class RecipeIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'amount']


class RecipeStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeStep
        fields = ['id', 'order', 'description', 'image']


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True)
    steps       = RecipeStepSerializer(many=True)
    author      = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = Recipe
        fields = [
            'id', 'author', 'title', 'description',
            'thumbnail_media', 'cook_time', 'servings',
            'is_public', 'ingredients', 'steps',
            'like_count', 'save_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        steps_data       = validated_data.pop('steps')

        recipe = Recipe.objects.create(**validated_data)

        for ingredient in ingredients_data:
            RecipeIngredient.objects.create(recipe=recipe, **ingredient)

        for step in steps_data:
            RecipeStep.objects.create(recipe=recipe, **step)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        steps_data       = validated_data.pop('steps', None)

        # Recipe 기본 필드 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

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