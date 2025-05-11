from django.test import TestCase
from django.db import connection
from ..models import FogServer
from ..tasks import update_keyword_frequency, perform_keyword_grouping
import logging

logger = logging.getLogger(__name__)

class KeywordGroupingTest(TestCase):
    def setUp(self):
        # 创建测试数据
        with connection.cursor() as cursor:
            # 创建测试轨迹点
            cursor.execute("""
                INSERT INTO tracks_table (track_id, point_id, latitude, longitude, date, time, keyword)
                VALUES 
                ('test1', 'p1', 0, 0, 1, 1, 'k1'),
                ('test2', 'p2', 0, 0, 1, 1, 'k2'),
                ('test3', 'p3', 0, 0, 1, 1, 'k1'),
                ('test4', 'p4', 0, 0, 1, 1, 'k2'),
                ('test5', 'p5', 0, 0, 1, 1, 'k3'),
                ('test6', 'p6', 0, 0, 1, 1, 'k3')
            """)
            
        # 创建测试服务器
        self.server1 = FogServer.objects.create(
            service_endpoint='http://test1.com',
            status='online'
        )
        self.server2 = FogServer.objects.create(
            service_endpoint='http://test2.com',
            status='online'
        )

    def test_keyword_frequency(self):
        """测试关键词频率统计"""
        # 执行频率统计
        success = update_keyword_frequency()
        self.assertTrue(success)
        
        # 验证结果
        from django.core.cache import cache
        freq_data = cache.get('keyword_freq')
        self.assertIsNotNone(freq_data)
        
        # 打印频率数据
        logger.info("Keyword frequency data:")
        for item in freq_data:
            logger.info(f"Keyword: {item['keyword']}, Frequency: {item['frequency']}")
            
        # 验证频率统计是否正确
        freq_dict = {item['keyword']: item['frequency'] for item in freq_data}
        self.assertEqual(freq_dict.get('k1', 0), 2)  # k1出现2次
        self.assertEqual(freq_dict.get('k2', 0), 2)  # k2出现2次
        self.assertEqual(freq_dict.get('k3', 0), 2)  # k3出现2次

    def test_keyword_grouping(self):
        """测试关键词分组"""
        # 先更新频率统计
        update_keyword_frequency()
        
        # 执行分组
        server_ids = [self.server1.id, self.server2.id]
        success = perform_keyword_grouping(server_ids)
        self.assertTrue(success)
        
        # 重新获取服务器数据
        server1 = FogServer.objects.get(id=self.server1.id)
        server2 = FogServer.objects.get(id=self.server2.id)
        
        # 打印分组结果
        logger.info(f"Server 1 keywords: {server1.keywords}")
        logger.info(f"Server 1 load: {server1.keyword_load}")
        logger.info(f"Server 2 keywords: {server2.keywords}")
        logger.info(f"Server 2 load: {server2.keyword_load}")
        
        # 验证结果
        self.assertTrue(server1.keywords)  # 确保有关键词
        self.assertTrue(server2.keywords)  # 确保有关键词
        self.assertGreater(server1.keyword_load, 0)  # 确保有负载
        self.assertGreater(server2.keyword_load, 0)  # 确保有负载
        
        # 验证负载总和接近100%
        total_load = server1.keyword_load + server2.keyword_load
        self.assertAlmostEqual(total_load, 100, delta=1)  # 允许1%的误差

    def tearDown(self):
        # 清理测试数据
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM tracks_table WHERE track_id LIKE 'test%'")
        FogServer.objects.all().delete() 