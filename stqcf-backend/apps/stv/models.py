from django.db import models
import uuid
import json


class STVQueryRequest(models.Model):
    """STV查询请求模型"""
    STATUS_CHOICES = (
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='请求ID')
    sstp_request_id = models.CharField(max_length=64, verbose_name='SSTP请求ID', help_text='关联的SSTP请求ID')
    time_span = models.IntegerField(verbose_name='时间跨度', help_text='查询的时间跨度限制(Ts)')
    query_ranges = models.TextField(verbose_name='查询范围', help_text='需要覆盖的查询范围列表(Rid)，JSON格式')
    candidate_trajectories = models.TextField(verbose_name='候选轨迹', help_text='SSTP筛选出的候选轨迹数据，JSON格式')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    def get_query_ranges(self):
        """获取查询范围列表"""
        return json.loads(self.query_ranges)
    
    def get_candidate_trajectories(self):
        """获取候选轨迹数据"""
        return json.loads(self.candidate_trajectories)
    
    class Meta:
        verbose_name = 'STV查询请求'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']


class STVQueryResult(models.Model):
    """STV查询结果模型"""
    query = models.OneToOneField(STVQueryRequest, on_delete=models.CASCADE, related_name='result', verbose_name='查询请求')
    result_trajectories = models.TextField(verbose_name='结果轨迹', help_text='满足条件的轨迹ID列表，JSON格式')
    processing_time = models.FloatField(verbose_name='处理时间', help_text='处理耗时(秒)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    def get_result_trajectories(self):
        """获取结果轨迹列表"""
        return json.loads(self.result_trajectories)
    
    class Meta:
        verbose_name = 'STV查询结果'
        verbose_name_plural = verbose_name
        ordering = ['-created_at'] 