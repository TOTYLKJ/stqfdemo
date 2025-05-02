from django.db import models

class Track(models.Model):
    track_id = models.CharField(max_length=100, db_index=True)
    point_id = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    date = models.IntegerField()
    time = models.IntegerField()
    keyword = models.CharField(max_length=255, blank=True)  # 使用逗号分隔的字符串存储关键词

    class Meta:
        db_table = 'tracks_table'
        unique_together = ('track_id', 'point_id')
        ordering = ['track_id', 'point_id']
        
    def __str__(self):
        return f"{self.track_id}-{self.point_id}"
    
    def get_keywords(self):
        """获取关键词列表"""
        return self.keyword.split(',') if self.keyword else []
    
    def set_keywords(self, keywords):
        """设置关键词列表"""
        self.keyword = ','.join(str(k) for k in keywords) if keywords else '' 