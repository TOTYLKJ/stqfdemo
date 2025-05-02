from .base import *

DEBUG = False

# 允许所有主机访问，因为我们在雾服务器环境中
ALLOWED_HOSTS = ['*']

# 禁用SSL重定向，因为我们在内部网络中使用HTTP
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.sstp': {  # 添加 SSTP 应用的日志器
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# 数据库配置 - 只保留 Cassandra
DATABASES = {
    'cassandra': {
        'ENGINE': 'django_cassandra_engine',
        'NAME': 'gko_space',
        'HOST': os.environ.get('CASSANDRA_URL', 'cassandra://localhost:9042'),
        'OPTIONS': {
            'replication': {
                'strategy_class': 'SimpleStrategy',
                'replication_factor': 1
            },
            'connection': {
                'keyspace': 'gko_space',
                'consistency': 'ONE'
            }
        }
    }
} 