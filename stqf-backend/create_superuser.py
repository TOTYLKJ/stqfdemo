import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gko_project.settings.development')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_superuser():
    try:
        superuser = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='admin123456'
        )
        print(f'超级用户创建成功！\n用户名: {superuser.username}\n邮箱: {superuser.email}')
    except Exception as e:
        print(f'创建超级用户时出错: {str(e)}')

if __name__ == '__main__':
    create_superuser() 