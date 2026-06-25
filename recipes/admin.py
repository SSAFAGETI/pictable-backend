from django.contrib import admin

from .models import Comment, Recipe, RecipeImage, RecipeIngredient, RecipeLike, RecipeSave, RecipeStep, Tag


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 1
    raw_id_fields = ('image',)


class RecipeImageInline(admin.TabularInline):
    model = RecipeImage
    extra = 1
    raw_id_fields = ('media_file',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'source_type', 'is_public', 'like_count', 'save_count', 'comment_count', 'created_at')
    list_filter = ('source_type', 'is_public', 'tags', 'created_at')
    search_fields = ('title', 'description', 'author__email', 'author__nickname', 'tags__name', 'ingredients__name')
    filter_horizontal = ('tags',)
    raw_id_fields = ('author', 'thumbnail_media')
    readonly_fields = ('like_count', 'save_count', 'comment_count', 'created_at', 'updated_at')
    inlines = (RecipeIngredientInline, RecipeStepInline, RecipeImageInline)


@admin.register(RecipeLike)
class RecipeLikeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('recipe__title', 'user__email', 'user__nickname')
    raw_id_fields = ('recipe', 'user')
    readonly_fields = ('created_at',)


@admin.register(RecipeSave)
class RecipeSaveAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('recipe__title', 'user__email', 'user__nickname')
    raw_id_fields = ('recipe', 'user')
    readonly_fields = ('created_at',)


@admin.register(RecipeImage)
class RecipeImageAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'media_file', 'sort_order', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('recipe__title', 'media_file__original_name', 'media_file__url')
    raw_id_fields = ('recipe', 'media_file')
    readonly_fields = ('created_at',)


@admin.register(RecipeStep)
class RecipeStepAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'order', 'description')
    list_filter = ('recipe',)
    search_fields = ('recipe__title', 'description')
    raw_id_fields = ('recipe', 'image')


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'name', 'amount')
    list_filter = ('name',)
    search_fields = ('recipe__title', 'name', 'amount')
    raw_id_fields = ('recipe',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'author', 'parent_comment', 'content', 'created_at', 'deleted_at')
    list_filter = ('created_at', 'deleted_at')
    search_fields = ('recipe__title', 'author__email', 'author__nickname', 'content')
    raw_id_fields = ('recipe', 'author', 'parent_comment')
    readonly_fields = ('created_at', 'updated_at')
