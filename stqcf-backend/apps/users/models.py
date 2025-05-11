import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('用户必须有邮箱地址')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', '管理员'),
        ('user', '普通用户'),
        ('operator', '运维人员'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('邮箱地址'), unique=True)
    username = models.CharField(_('用户名'), max_length=150, unique=True)
    role = models.CharField(_('角色'), max_length=20, choices=ROLE_CHOICES, default='user')
    is_active = models.BooleanField(_('是否激活'), default=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    last_login = models.DateTimeField(_('最后登录'), null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='custom_user_set',
        related_query_name='custom_user',
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('用户')
        verbose_name_plural = _('用户')
        db_table = 'users'

    def __str__(self):
        return self.email

    def get_tokens_for_user(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

class AuditLog(models.Model):
    OPERATION_CHOICES = (
        ('login', '登录'),
        ('query', '查询'),
        ('export', '导出'),
        ('delete', '删除'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    operation = models.CharField(_('操作类型'), max_length=20, choices=OPERATION_CHOICES)
    parameters = models.JSONField(_('操作参数'), null=True, blank=True)
    result = models.CharField(_('操作结果'), max_length=20)
    ip_address = models.GenericIPAddressField(_('IP地址'))
    timestamp = models.DateTimeField(_('操作时间'), auto_now_add=True)

    class Meta:
        verbose_name = _('审计日志')
        verbose_name_plural = _('审计日志')
        db_table = 'audit_logs'
        ordering = ['-timestamp'] 