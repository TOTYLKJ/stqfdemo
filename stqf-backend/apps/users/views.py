from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging
from .models import AuditLog
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    ChangePasswordSerializer, AuditLogSerializer
)
from .permissions import IsAdmin, IsOperator, IsSelfOrAdmin

logger = logging.getLogger(__name__)
User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        elif self.action in ['list', 'create']:
            return [IsAdmin()]
        return [IsSelfOrAdmin()]

    def perform_create(self, serializer):
        user = serializer.save()
        self._create_audit_log(user, 'create', 'success')

    def perform_update(self, serializer):
        user = serializer.save()
        self._create_audit_log(user, 'update', 'success')

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            if not user.check_password(serializer.data.get('old_password')):
                return Response({'old_password': ['密码错误']}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(serializer.data.get('new_password'))
            user.save()
            self._create_audit_log(user, 'change_password', 'success')
            return Response({'status': 'success'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _create_audit_log(self, user, operation, result):
        AuditLog.objects.create(
            user=user,
            operation=operation,
            parameters=None,
            result=result,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin|IsOperator]

    def get_queryset(self):
        queryset = AuditLog.objects.all()
        if self.request.user.role == 'operator':
            queryset = queryset.filter(user=self.request.user)
        return queryset.select_related('user')

class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        logger.debug('收到GET请求：%s', request.path)
        return Response({'detail': '请使用POST方法进行登录'})

    def post(self, request, *args, **kwargs):
        logger.debug('收到POST请求：%s，数据：%s', request.path, request.data)
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            logger.warning('登录失败：邮箱或密码为空')
            return Response({'error': '邮箱和密码不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning('登录失败：用户不存在 - %s', email)
            return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not user.check_password(password):
            logger.warning('登录失败：密码错误 - %s', email)
            return Response({'error': '密码错误'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            logger.warning('登录失败：账户已禁用 - %s', email)
            return Response({'error': '账户已被禁用'}, status=status.HTTP_403_FORBIDDEN)

        user.last_login = timezone.now()
        user.save()

        AuditLog.objects.create(
            user=user,
            operation='login',
            result='success',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        logger.info('用户登录成功：%s', email)
        tokens = user.get_tokens_for_user()
        return Response({
            'user': UserSerializer(user).data,
            'access': tokens['access'],
            'refresh': tokens['refresh']
        })

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer

    def post(self, request, *args, **kwargs):
        logger.debug('收到注册请求：%s', request.data)
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            logger.info('用户注册成功：%s', user.email)
            
            # 创建审计日志
            AuditLog.objects.create(
                user=user,
                operation='register',
                result='success',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # 返回用户信息和token
            tokens = user.get_tokens_for_user()
            return Response({
                'user': UserSerializer(user).data,
                'access': tokens['access'],
                'refresh': tokens['refresh']
            }, status=status.HTTP_201_CREATED)
        
        logger.warning('用户注册失败：%s', serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 