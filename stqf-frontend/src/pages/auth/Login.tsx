import React from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { login } from '@/api/auth';
import { setAuth } from '@/store/slices/authSlice';

interface LoginForm {
  email: string;
  password: string;
}

const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();

  // 获取用户之前尝试访问的页面
  const from = location.state?.from?.pathname || '/dashboard';

  const onFinish = async (values: LoginForm) => {
    try {
      const response = await login(values);
      console.log('Login response:', response);

      dispatch(
        setAuth({
          token: response.access,
          refresh_token: response.refresh,
          user: response.user,
        })
      );

      message.success('Login successful');
      // 登录成功后重定向到之前的页面
      navigate(from, { replace: true });
    } catch (error: any) {
      console.error('Login error:', error);
      const errorMessage = error.response?.data?.error || 'Login failed, please try again later';
      message.error(errorMessage);
    }
  };

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: '#f0f2f5',
      }}
    >
      <Card style={{ width: 400 }}>
        <h2 style={{ textAlign: 'center', marginBottom: 30 }}>GKO Trajectory Query System</h2>
        <Form name='login' onFinish={onFinish}>
          <Form.Item
            name='email'
            rules={[
              { required: true, message: 'Please enter your email' },
              { type: 'email', message: 'Please enter a valid email address' },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder='Email' size='large' />
          </Form.Item>

          <Form.Item
            name='password'
            rules={[{ required: true, message: 'Please enter your password' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder='Password' size='large' />
          </Form.Item>

          <Form.Item>
            <Button type='primary' htmlType='submit' block size='large'>
              Login
            </Button>
          </Form.Item>

          <div style={{ textAlign: 'center' }}>
            Don&apos;t have an account yet?
            <a onClick={() => navigate('/register')}>Register now</a>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
