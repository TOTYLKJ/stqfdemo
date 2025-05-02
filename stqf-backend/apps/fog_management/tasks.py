from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Avg
from .models import FogServer
from apps.data_management.models import Track
import logging
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger
from django.db import connection

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def update_keyword_frequency(self):
    """更新关键词频率统计"""
    try:
        # 使用原生SQL查询统计关键词频率
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT keyword AS keywords, COUNT(*) AS frequency
                FROM tracks_table
                GROUP BY keyword
                ORDER BY frequency DESC
            """)
            keyword_freq = [
                {'keyword': row[0].strip(), 'frequency': row[1]}
                for row in cursor.fetchall()
                if row[0] and row[0].strip()  # 排除空字符串
            ]

        # 缓存结果
        cache.set('keyword_freq', keyword_freq, timeout=300)  # 5分钟过期
        logger.info(f"Updated keyword frequency stats: {len(keyword_freq)} keywords")
        return True
    except Exception as e:
        logger.error(f"Error updating keyword frequency: {str(e)}")
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for keyword frequency update")
        return False

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def perform_keyword_grouping(self, server_ids, strategy='frequency_greedy'):
    """执行关键词分组"""
    logger.info(f"Starting keyword grouping for servers: {server_ids}")
    
    if strategy != 'frequency_greedy':
        logger.error(f"Unsupported grouping strategy: {strategy}")
        raise ValueError('Unsupported grouping strategy')

    try:
        with transaction.atomic():
            # 获取指定的在线服务器
            online_servers = FogServer.objects.filter(
                id__in=server_ids,
                status='online'
            ).order_by('keyword_load')
            
            if not online_servers.exists():
                logger.warning("No online servers available for grouping")
                return False

            server_count = online_servers.count()
            logger.info(f"Found {server_count} online servers for grouping")

            # 清空现有分配
            for server in online_servers:
                logger.info(f"Clearing server {server.id} previous assignments")
                server.keywords = ''
                server.keyword_load = 0
                server.save()
            
            # 直接从数据库获取关键词频率
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT keyword, COUNT(*) as frequency
                    FROM tracks_table
                    WHERE keyword IS NOT NULL AND keyword != ''
                    GROUP BY keyword
                    ORDER BY frequency DESC
                """)
                keyword_freq = [
                    {'keyword': row[0], 'frequency': row[1]}
                    for row in cursor.fetchall()
                ]

            if not keyword_freq:
                logger.error("No keyword frequency data available")
                return False

            logger.info(f"Got {len(keyword_freq)} keywords from database")

            # 计算总频率
            total_frequency = sum(item['frequency'] for item in keyword_freq)
            if total_frequency == 0:
                logger.error("Total frequency is 0")
                return False

            logger.info(f"Total frequency: {total_frequency}")

            # 初始化服务器关键词映射
            server_keywords = {server.id: [] for server in online_servers}
            server_loads = {server.id: 0 for server in online_servers}

            # 贪心分配
            for kw_data in keyword_freq:
                keyword = kw_data['keyword']
                freq = kw_data['frequency']
                
                # 选择负载最低的服务器
                target_server = min(online_servers, key=lambda s: server_loads[s.id])
                
                # 更新服务器关键词列表
                server_keywords[target_server.id].append(keyword)
                # 更新负载（累加频率的百分比）
                new_load = (freq / total_frequency) * 100
                server_loads[target_server.id] += new_load
                logger.debug(f"Assigned keyword '{keyword}' (freq: {freq}) to server {target_server.id}, new load: {server_loads[target_server.id]:.2f}%")

            # 保存分配结果到数据库
            for server in online_servers:
                keywords = server_keywords[server.id]
                if keywords:  # 只在有关键词时更新
                    logger.info(f"Saving {len(keywords)} keywords to server {server.id}")
                    logger.debug(f"Keywords for server {server.id}: {keywords[:5]}...")
                    logger.debug(f"Load for server {server.id}: {server_loads[server.id]:.2f}%")
                    
                    server.keywords = ','.join(keywords)
                    server.keyword_load = round(server_loads[server.id], 2)
                    server.save()
                    
                    # 验证保存是否成功
                    saved_server = FogServer.objects.get(id=server.id)
                    logger.info(f"Verified server {server.id} save: keywords_count={len(saved_server.keywords.split(',') if saved_server.keywords else [])}, load={saved_server.keyword_load}")

            return True

    except Exception as e:
        logger.error(f"Error performing keyword grouping: {str(e)}", exc_info=True)
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for keyword grouping")
        return False 