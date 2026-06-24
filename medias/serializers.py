from rest_framework import serializers
from .models import MediaFile


class MediaFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    
    class Meta:
        model  = MediaFile
        fields = ['id', 'url']

    def get_url(self, obj):
        # http://54.180.86.58:8000/media/thumbnail/xxx.jpg
        # → /media/thumbnail/xxx.jpg
        if obj.url and obj.url.startswith('http'):
            from urllib.parse import urlparse
            parsed = urlparse(obj.url)
            return parsed.path  # /media/thumbnail/xxx.jpg 만 반환
        return obj.url