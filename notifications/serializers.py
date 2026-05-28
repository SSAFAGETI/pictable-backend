from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    actor = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'actor', 'recipe', 'comment',
            'type', 'title', 'message',
            'is_read', 'created_at', 'read_at',
        ]