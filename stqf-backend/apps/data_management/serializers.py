from rest_framework import serializers
from .models import Track

class TrackSerializer(serializers.ModelSerializer):
    keywords = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)

    class Meta:
        model = Track
        fields = ['track_id', 'point_id', 'latitude', 'longitude', 'date', 'time', 'keyword', 'keywords']
        read_only_fields = ['point_id']  # point_id 由系统自动生成 

    def to_representation(self, instance):
        """将关键词字符串转换为列表"""
        ret = super().to_representation(instance)
        ret['keywords'] = instance.get_keywords()
        return ret

    def create(self, validated_data):
        """处理创建时的关键词列表"""
        keywords = validated_data.pop('keywords', None)
        instance = super().create(validated_data)
        if keywords is not None:
            instance.set_keywords(keywords)
            instance.save()
        return instance

    def update(self, instance, validated_data):
        """处理更新时的关键词列表"""
        keywords = validated_data.pop('keywords', None)
        instance = super().update(instance, validated_data)
        if keywords is not None:
            instance.set_keywords(keywords)
            instance.save()
        return instance 