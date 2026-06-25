from django.contrib import admin

from .models import IngredientAlias, IngredientCatalog, IngredientDetectionItem, IngredientDetectionJob, MediaFile


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'uploader_user', 'mime_type', 'purpose', 'size_bytes', 'created_at')
    list_filter = ('purpose', 'mime_type', 'created_at')
    search_fields = ('original_name', 'url', 'uploader_user__email', 'uploader_user__nickname')
    raw_id_fields = ('uploader_user',)
    readonly_fields = ('created_at',)


@admin.register(IngredientCatalog)
class IngredientCatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'category')
    readonly_fields = ('created_at',)


@admin.register(IngredientAlias)
class IngredientAliasAdmin(admin.ModelAdmin):
    list_display = ('alias_name', 'ingredient_name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('alias_name', 'ingredient_name')
    readonly_fields = ('created_at',)


class IngredientDetectionItemInline(admin.TabularInline):
    model = IngredientDetectionItem
    extra = 1
    raw_id_fields = ('ingredient',)
    readonly_fields = ('created_at',)


@admin.register(IngredientDetectionJob)
class IngredientDetectionJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'media_file', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at', 'completed_at')
    search_fields = ('user__email', 'user__nickname', 'media_file__original_name', 'items__detected_name')
    raw_id_fields = ('user', 'media_file')
    readonly_fields = ('created_at',)
    inlines = (IngredientDetectionItemInline,)


@admin.register(IngredientDetectionItem)
class IngredientDetectionItemAdmin(admin.ModelAdmin):
    list_display = ('detection_job', 'detected_name', 'ingredient', 'confidence', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('detected_name', 'ingredient__name', 'detection_job__user__email')
    raw_id_fields = ('detection_job', 'ingredient')
    readonly_fields = ('created_at',)
