import React from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { register } from '@/api/auth';
import { setAuth } from '@/store/slices/authSlice';

interface RegisterForm {
  username: string;
  email: string;
  password: string;
  password2: string;
}

const Register: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  // Password validation rules
  const validatePassword = (_: any, value: string) => {
    if (!value) {
      return Promise.reject('Please enter a password');
    }
    if (value.length < 8) {
      return Promise.reject('Password must be at least 8 characters');
    }
    if (/^\d+$/.test(value)) {
      return Promise.reject('Password cannot contain only numbers');
    }
    if (/^[a-zA-Z]+$/.test(value)) {
      return Promise.reject('Password cannot contain only letters');
    }
    if (/^[a-zA-Z0-9]+$/.test(value)) {
      return Promise.reject('Password must include special characters');
    }
    return Promise.resolve();
  };

  // Confirm password validation rules
  const validateConfirmPassword = ({ getFieldValue }: any) => ({
    validator(_: any, value: string) {
      if (!value) {
        return Promise.reject('Please confirm your password');
      }
      if (value !== getFieldValue('password')) {
        return Promise.reject('The two passwords do not match');
      }
      return Promise.resolve();
    },
  });

  const onFinish = async (values: RegisterForm) => {
    try {
      const response = await register(values);

      // Auto login after successful registration
      dispatch(
        setAuth({
          token: response.access,
          refresh_token: response.refresh,
          user: response.user,
        })
      );

      message.success('Registration successful');
      navigate('/dashboard');
    } catch (error: any) {
      console.error('Registration error:', error);
      const errorData = error.response?.data;
      if (errorData) {
        // Handle specific error messages from backend
        const errorMessages = Object.entries(errorData).map(([field, errors]) => {
          if (Array.isArray(errors)) {
            return errors.join(', ');
          }
          return errors;
        });
        message.error(errorMessages.join('; '));
      } else {
        message.error('Registration failed, please try again later');
      }
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
        <h2 style={{ textAlign: 'center', marginBottom: 30 }}>Register New Account</h2>
        <Form name='register' onFinish={onFinish}>
          <Form.Item
            name='username'
            rules={[
              { required: true, message: 'Please enter a username' },
              { min: 3, message: 'Username must be at least 3 characters' },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder='Username' size='large' />
          </Form.Item>

          <Form.Item
            name='email'
            rules={[
              { required: true, message: 'Please enter an email' },
              { type: 'email', message: 'Please enter a valid email address' },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder='Email' size='large' />
          </Form.Item>

          <Form.Item
            name='password'
            rules={[{ validator: validatePassword }]}
            help='Password must be at least 8 characters and include letters, numbers, and special characters'
          >
            <Input.Password prefix={<LockOutlined />} placeholder='Password' size='large' />
          </Form.Item>

          <Form.Item name='password2' dependencies={['password']} rules={[validateConfirmPassword]}>
            <Input.Password prefix={<LockOutlined />} placeholder='Confirm Password' size='large' />
          </Form.Item>

          <Form.Item>
            <Button type='primary' htmlType='submit' block size='large'>
              Register
            </Button>
          </Form.Item>

          <div style={{ textAlign: 'center' }}>
            Already have an account?
            <a onClick={() => navigate('/login')}>Login now</a>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default Register;
