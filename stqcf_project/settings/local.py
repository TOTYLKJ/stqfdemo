from .base import *

# 添加STV应用
INSTALLED_APPS += ['apps.stv']

# STV模块配置
STV_SERVICE_URL = 'http://localhost:8000/api/stv/query/'
SSTP_SERVICE_URL = 'http://localhost:8000/api/sstp' 