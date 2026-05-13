from django.db import models
from django.conf import settings


class Recipe(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recipes')
    thumbnail_media = models.ForeignKey('medias.MediaFile', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    servings = models.PositiveSmallIntegerField(default=2)
    cook_time = models.PositiveIntegerField(help_text='분 단위', null=True, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class RecipeStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveSmallIntegerField()
    description = models.TextField()
    image = models.ImageField(upload_to='recipes/steps/', blank=True, null=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.recipe.title} - step {self.order}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=100)
    amount = models.CharField(max_length=50)  # "2컵", "100g" 자유 입력

    def __str__(self):
        return f'{self.name} {self.amount}'