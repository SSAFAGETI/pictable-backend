from django.db import models
from django.conf import settings

class MediaFile(models.Model):
    uploader_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    url = models.URLField(max_length=700)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120)
    purpose = models.CharField(max_length=50, blank=True)  # 'thumbnail', 'step' 등
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
class IngredientCatalog(models.Model):
    name = models.CharField(max_length=80)
    category = models.CharField(max_length=60, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingredient_catalog'

class IngredientAlias(models.Model):
    ingredient = models.ForeignKey(
        IngredientCatalog, on_delete=models.CASCADE, related_name='aliases'
    )
    alias = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingredient_aliases'

class IngredientDetectionJob(models.Model):
    STATUS_CHOICES = [
        ('pending',    '대기중'),
        ('processing', '처리중'),
        ('completed',  '완료'),
        ('failed',     '실패'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    media_file = models.ForeignKey(
        MediaFile, on_delete=models.CASCADE
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ingredient_detection_jobs'

class IngredientDetectionItem(models.Model):
    detection_job = models.ForeignKey(
        IngredientDetectionJob, on_delete=models.CASCADE, related_name='items'
    )
    ingredient = models.ForeignKey(
        IngredientCatalog, on_delete=models.SET_NULL, null=True, blank=True
    )
    detected_name = models.CharField(max_length=80)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingredient_detection_items'