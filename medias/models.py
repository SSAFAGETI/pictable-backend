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