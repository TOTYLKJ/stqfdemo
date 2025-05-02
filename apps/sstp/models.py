from django.db import models
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
import pickle
import logging

logger = logging.getLogger(__name__)

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
        keyspace = 'gko_space'

class TrajectoryDate(Model):
    """轨迹日期模型（加密数据）"""
    keyword = columns.Integer(primary_key=True, partition_key=True)
    node_id = columns.Integer(primary_key=True, partition_key=True)
    traj_id = columns.Blob(primary_key=True)
    t_date = columns.Blob()  # 改为小写
    latitude = columns.Blob()  # 加密的纬度
    longitude = columns.Blob()  # 加密的经度
    time = columns.Blob()  # 加密的时间戳
    
    class Meta:
        app_label = 'sstp'
        db_table = 'TrajectoryDate'
        keyspace = 'gko_space'
        managed = False  # 禁用Django的自动命名转换
        
    def save(self, *args, **kwargs):
        """重写save方法，添加数据验证"""
        # 验证必要字段
        if self.traj_id is None:
            raise ValueError("traj_id不能为None")
            
        if self.t_date is None:  # 改为小写
            raise ValueError("t_date不能为None")  # 改为小写
            
        # 打印字段信息
        print("\n=== 保存轨迹数据 ===")
        print(f"keyword: {self.keyword}, 类型: {type(self.keyword)}")
        print(f"node_id: {self.node_id}, 类型: {type(self.node_id)}")
        print(f"traj_id: {self.traj_id}, 类型: {type(self.traj_id)}")
        print(f"t_date: {self.t_date}, 类型: {type(self.t_date)}")  # 改为小写
        
        # 确保数据类型正确
        if not isinstance(self.traj_id, bytes):
            print("警告：traj_id不是bytes类型，尝试转换...")
            try:
                self.traj_id = pickle.dumps(self.traj_id)
                print(f"traj_id转换成功: {self.traj_id}")
            except Exception as e:
                print(f"traj_id转换失败: {str(e)}")
                raise
                
        if not isinstance(self.t_date, bytes):  # 改为小写
            print("警告：t_date不是bytes类型，尝试转换...")  # 改为小写
            try:
                self.t_date = pickle.dumps(self.t_date)  # 改为小写
                print(f"t_date转换成功: {self.t_date}")  # 改为小写
            except Exception as e:
                print(f"t_date转换失败: {str(e)}")  # 改为小写
                raise
                
        # 调用原始的save方法
        super().save(*args, **kwargs)

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