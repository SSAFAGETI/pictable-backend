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
    like_count = models.IntegerField(default=0)
    save_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class RecipeLike(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='liked_recipes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('recipe', 'user')
        
class RecipeSave(models.Model):
    recipe     = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='saves')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_recipes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('recipe', 'user')

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
    
class Comment(models.Model):
    recipe            = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='comments')
    author            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    parent_comment    = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content           = models.CharField(max_length=500)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)
    deleted_at        = models.DateTimeField(null=True, blank=True)