import React, { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Button, message, Spin } from 'antd';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '@/store';
import { updateUser } from '@/store/slices/authSlice';
import { UserOutlined, MailOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '@/api/config';

const { TabPane } = Tabs;

const Profile: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const user = useSelector((state: RootState) => state.auth.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  // 基本信息表单
  const [basicForm] = Form.useForm();
  // 密码修改表单
  const [passwordForm] = Form.useForm();

  // 检查用户登录状态
  useEffect(() => {
    if (!user?.id) {
      message.error('Please login first');
      navigate('/login');
    }
  }, [user, navigate]);

  // 获取最新的用户信息
  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        if (!user?.id) {
          setPageLoading(false);
          return;
        }
        const response = await api.get(`/api/users/list/${user.id}/`);
        dispatch(updateUser(response.data));
        // 更新表单的初始值
        basicForm.setFieldsValue({
          username: response.data.username,
          email: response.data.email,
        });
      } catch (error: any) {
        const errorMsg = error.response?.data?.error || 'Failed to get user information';
        message.error(errorMsg);
        if (error.response?.status === 401) {
          navigate('/login');
        }
      } finally {
        setPageLoading(false);
      }
    };

    fetchUserInfo();
  }, [user?.id, dispatch, basicForm, navigate]);

  // 更新基本信息
  const handleUpdateBasicInfo = async (values: { username: string; email: string }) => {
    if (!user?.id) {
      message.error('Invalid user information, please login again');
      navigate('/login');
      return;
    }

    try {
      setLoading(true);
      const response = await api.patch(`/api/users/list/${user.id}/`, values);
      dispatch(updateUser(response.data));
      message.success('Profile information updated successfully');
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Update failed, please try again later';
      message.error(errorMsg);
      if (error.response?.status === 401) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  // 修改密码
  const handleChangePassword = async (values: {
    old_password: string;
    new_password: string;
    new_password2: string;
  }) => {
    if (!user?.id) {
      message.error('Invalid user information, please login again');
      navigate('/login');
      return;
    }

    try {
      setLoading(true);
      await api.post(`/api/users/list/${user.id}/change_password/`, values);
      message.success('Password changed successfully');
      passwordForm.resetFields();
    } catch (error: any) {
      console.error('修改密码错误:', error);
      const errorMsg =
        error.response?.data?.error || 'Password change failed, please try again later';
      message.error(errorMsg);
      if (error.response?.status === 401) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  if (pageLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size='large' tip='加载中...' />
      </div>
    );
  }

  // 如果没有用户信息，不渲染页面内容
  if (!user?.id) {
    return null;
  }

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <Card title='My Profile'>
        <Tabs defaultActiveKey='basic'>
          <TabPane tab='Basic Information' key='basic'>
            <Form
              form={basicForm}
              layout='vertical'
              initialValues={{
                username: user?.username,
                email: user?.email,
              }}
              onFinish={handleUpdateBasicInfo}
            >
              <Form.Item
                name='username'
                label='Username'
                rules={[{ required: true, message: 'Please enter username' }]}
              >
                <Input prefix={<UserOutlined />} placeholder='Username' />
              </Form.Item>

              <Form.Item
                name='email'
                label='Email'
                rules={[
                  { required: true, message: 'Please enter email' },
                  { type: 'email', message: 'Please enter a valid email address' },
                ]}
              >
                <Input prefix={<MailOutlined />} placeholder='Email' disabled />
              </Form.Item>

              <Form.Item>
                <Button type='primary' htmlType='submit' loading={loading}>
                  Save Changes
                </Button>
              </Form.Item>
            </Form>
          </TabPane>

          <TabPane tab='Change Password' key='password'>
            <Form form={passwordForm} layout='vertical' onFinish={handleChangePassword}>
              <Form.Item
                name='old_password'
                label='Current Password'
                rules={[{ required: true, message: 'Please enter current password' }]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder='Current Password' />
              </Form.Item>

              <Form.Item
                name='new_password'
                label='New Password'
                rules={[
                  { required: true, message: 'Please enter new password' },
                  { min: 8, message: 'Password must be at least 8 characters' },
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder='New Password' />
              </Form.Item>

              <Form.Item
                name='new_password2'
                label='Confirm New Password'
                dependencies={['new_password']}
                rules={[
                  { required: true, message: 'Please confirm your password' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('The two passwords do not match'));
                    },
                  }),
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder='Confirm New Password' />
              </Form.Item>

              <Form.Item>
                <Button type='primary' htmlType='submit' loading={loading}>
                  Change Password
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default Profile;
