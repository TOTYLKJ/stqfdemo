from django.db import models
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class FogServer(models.Model):
    STATUS_CHOICES = (
        ('online', '在线'),
        ('offline', '离线'),
        ('maintenance', '维护中'),
    )

    id = models.AutoField(primary_key=True)
    service_endpoint = models.URLField(
        max_length=255,
        unique=True,
        validators=[URLValidator()],
        help_text='服务器接口地址'
    )
    keywords = models.TextField(
        blank=True,
        help_text='分配的关键词列表，以逗号分隔'
    )
    keyword_load = models.FloatField(
        default=0,
        help_text='关键词负载百分比'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline',
        help_text='服务器状态'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fog_servers'
        ordering = ['-created_at']
        verbose_name = '雾服务器'
        verbose_name_plural = '雾服务器'

    def __str__(self):
        return f"{self.service_endpoint} ({self.status})"

    def clean(self):
        if self.keyword_load < 0 or self.keyword_load > 100:
            raise ValidationError('关键词负载必须在0-100之间')

    def get_keywords_list(self):
        """获取关键词列表"""
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(',') if k.strip()]

    def set_keywords_list(self, keywords_list):
        """设置关键词列表"""
        self.keywords = ','.join(keywords_list)
