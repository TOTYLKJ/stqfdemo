from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import STVQueryResult
from .integration import SSTPIntegration

logger = logging.getLogger(__name__)

@receiver(post_save, sender=STVQueryResult)
def notify_sstp_on_result_save(sender, instance, created, **kwargs):
    """当STV查询结果保存时，通知SSTP模块"""
    if created:  # 只在创建新结果时触发
        logger.info(f"STV查询结果已保存，准备通知SSTP模块，查询ID: {instance.query.id}")
        
        try:
            # 获取SSTP请求ID和结果轨迹
            sstp_request_id = instance.query.sstp_request_id
            result_trajectories = instance.get_result_trajectories()
            
            # 通知SSTP模块
            success, result = SSTPIntegration.notify_sstp_result(
                sstp_request_id, result_trajectories
            )
            
            if success:
                logger.info(f"成功通知SSTP模块查询结果: {result}")
            else:
                logger.error(f"通知SSTP模块查询结果失败: {result}")
                
        except Exception as e:
            logger.error(f"通知SSTP模块查询结果异常: {str(e)}", exc_info=True) 