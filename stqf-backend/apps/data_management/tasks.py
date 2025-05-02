from celery import shared_task
from django.core.cache import cache
from .models import Track
from .views import STATS_CACHE_KEY, STATS_CACHE_TIMEOUT

@shared_task
def update_track_statistics():
    """定期更新轨迹统计数据的缓存"""
    total_points = Track.objects.count()
    
    # 使用数据库聚合来优化关键词统计
    keywords = Track.objects.exclude(keyword='').values_list('keyword', flat=True)
    unique_keywords = set()
    for kw in keywords:
        if kw:
            unique_keywords.update(kw.split(','))
    unique_keywords.discard('')
    
    stats = {
        'total_points': total_points,
        'total_keywords': len(unique_keywords),
        'keywords_list': sorted(list(unique_keywords))
    }
    
    # 更新缓存
    cache.set(STATS_CACHE_KEY, stats, STATS_CACHE_TIMEOUT)
    return stats 