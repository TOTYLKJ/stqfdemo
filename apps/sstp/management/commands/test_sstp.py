from django.core.management.base import BaseCommand
from apps.sstp.test_sstp_interactive import main

class Command(BaseCommand):
    help = '运行SSTP测试程序'

    def handle(self, *args, **options):
        main() 