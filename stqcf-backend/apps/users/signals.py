from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_audit_log(sender, instance, created, **kwargs):
    """
    当用户被创建时，创建审计日志
    """
    if created and not instance.is_superuser:  # 不为超级用户创建审计日志
        AuditLog.objects.create(
            user=instance,
            operation='create',
            result='success',
            ip_address='system'
        ) 