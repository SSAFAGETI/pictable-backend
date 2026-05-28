from rest_framework import serializers
from accounts.models import User

class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'nickname',
            'profile_image_url', 'provider',
            'role', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'provider', 'role', 'created_at', 'updated_at']