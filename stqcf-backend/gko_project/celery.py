import os
from celery import Celery
from django.conf import settings

# 设置默认Django settings模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')

app = Celery('gko_project')

# 使用Django的settings文件配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 设置任务重试策略
app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=False,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_connection_timeout=30,
    
    # 结果后端配置
    result_backend='redis://localhost:6379/0',
    result_expires=3600,  # 结果过期时间：1小时
    
    # 任务执行配置
    task_track_started=True,  # 追踪任务开始状态
    task_time_limit=300,      # 任务超时时间：5分钟
    task_soft_time_limit=240, # 软超时时间：4分钟
    
    # Worker并发配置
    worker_prefetch_multiplier=1,  # 防止worker过度预取任务
    worker_max_tasks_per_child=200,# 防止内存泄漏
)

# 自动发现任务
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 