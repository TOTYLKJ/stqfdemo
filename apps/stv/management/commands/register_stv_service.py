from django.core.management.base import BaseCommand
from stv.integration import SSTPIntegration

class Command(BaseCommand):
    help = '向SSTP模块注册STV服务'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('开始注册STV服务...'))
        
        success, result = SSTPIntegration.register_stv_service()
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'STV服务注册成功: {result}'))
        else:
            self.stdout.write(self.style.ERROR(f'STV服务注册失败: {result}')) 