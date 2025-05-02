from rest_framework import serializers
from .models import FogServer

class FogServerSerializer(serializers.ModelSerializer):
    keywords = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        read_only=True
    )

    class Meta:
        model = FogServer
        fields = ['id', 'service_endpoint', 'keywords', 'keyword_load', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'keyword_load', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """自定义输出格式"""
        ret = super().to_representation(instance)
        ret['keywords'] = instance.get_keywords_list()
        return ret

class FogServerCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FogServer
        fields = ['service_endpoint', 'status']

    def validate_service_endpoint(self, value):
        """验证服务端点"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError('服务端点必须是有效的HTTP(S)地址')
        return value 