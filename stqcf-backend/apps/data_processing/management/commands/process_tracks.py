from django.core.management.base import BaseCommand
from ...tasks import process_tracks_data

class Command(BaseCommand):
    help = '从MySQL的tracks_table处理数据并存储到Cassandra的trajectorydate表'

    def handle(self, *args, **options):
        self.stdout.write('开始处理数据...')
        try:
            process_tracks_data()
            self.stdout.write(self.style.SUCCESS('数据处理成功完成！'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'处理数据时出错: {str(e)}')) 