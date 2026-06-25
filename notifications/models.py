from django.db import models
from django.conf import settings

class Notification(models.Model):
    TYPE_CHOICES = [
        ('system', '시스템'),
        ('like', '좋아요'),
        ('comment', '댓글'),
        ('reply', '답글'),
        ('follow', '팔로우'),
    ]

    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sent_notifications')
    recipe = models.ForeignKey('recipes.Recipe',  on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey('recipes.Comment', on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
