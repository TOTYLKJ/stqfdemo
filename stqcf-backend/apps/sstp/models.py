from django.db import models
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model

# 这里我们不需要创建新的数据模型，因为我们将使用现有的OctreeNode和TrajectoryDate表
# 但我们需要定义这些表的模型，以便在SSTP模块中使用

class OctreeNode(Model):
    """八叉树节点模型（明文数据）"""
    node_id = columns.Integer(primary_key=True)
    parent_id = columns.Integer(index=True)
    level = columns.Integer(index=True)
    is_leaf = columns.Integer()
    MC = columns.List(value_type=columns.Integer)  # Morton码
    GC = columns.List(value_type=columns.Integer)  # 网格坐标
    
    class Meta:
        app_label = 'sstp'
        db_table = 'OctreeNode'
        keyspace = 'gko_db'  # 添加keyspace配置

class TrajectoryDate(Model):
    """轨迹日期模型（加密数据）"""
    keyword = columns.Blob(primary_key=True, partition_key=True)
    node_id = columns.Integer(primary_key=True, partition_key=True)
    traj_id = columns.Blob(primary_key=True)
    t_date = columns.Blob()
    latitude = columns.Blob()  # 加密的纬度
    longitude = columns.Blob()  # 加密的经度
    time = columns.Blob()  # 加密的时间戳
    
    class Meta:
        app_label = 'sstp'
        db_table = 'TrajectoryDate'
        keyspace = 'gko_db'  # 添加keyspace配置
        managed = False  # 禁用Django的自动命名转换

class QueryRequest(models.Model):
    """查询请求记录模型"""
    rid = models.CharField(max_length=64, primary_key=True, verbose_name="请求ID")
    fog_id = models.IntegerField(verbose_name="雾服务器ID")
    keyword = models.BinaryField(verbose_name="关键词")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    status = models.CharField(max_length=20, default="pending", verbose_name="状态")
    
    class Meta:
        app_label = 'sstp'
        verbose_name = "查询请求"
        verbose_name_plural = "查询请求"
        
    def __str__(self):
        return f"查询请求 {self.rid} - 雾服务器 {self.fog_id}"
