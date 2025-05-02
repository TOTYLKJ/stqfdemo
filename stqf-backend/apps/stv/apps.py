from django.apps import AppConfig


class STVConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stv'
    verbose_name = '安全时间跨度验证'
    
    def ready(self):
        """应用就绪时执行"""
        # 导入信号处理器
        import apps.stv.signals 