import React, { useEffect, useState } from 'react';
import { Table, Button, Tag, Select, message, Space, Card } from 'antd';
import { useSelector } from 'react-redux';
import { RootState } from '@/store';
import { useNavigate } from 'react-router-dom';
import api from '@/api/config';

const { Option } = Select;

// User interface
interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  date_joined: string;
}

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const currentUser = useSelector((state: RootState) => state.auth.user);
  const navigate = useNavigate();

  // Get user list
  const fetchUsers = async () => {
    // Check if current user and token exist
    if (!currentUser?.id || !localStorage.getItem('token')) {
      message.error('Please login first');
      navigate('/login');
      return;
    }

    // Check if user is admin
    if (currentUser.role !== 'admin') {
      message.error('Admin permission required');
      navigate('/dashboard');
      return;
    }

    try {
      setLoading(true);
      const response = await api.get('/api/users/list/');
      console.log('API Response:', response);
      // Get results array from paginated data
      const userData = Array.isArray(response.data.results) ? response.data.results : [];
      console.log('Processed User Data:', userData);
      setUsers(userData);
    } catch (error: any) {
      console.error('Error fetching users:', error);
      const errorMsg = error.response?.data?.error || 'Failed to get user list';
      message.error(errorMsg);
      if (error.response?.status === 401 || error.response?.status === 403) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [currentUser]); // Add currentUser as dependency

  // Change user role
  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await api.patch(`/api/users/list/${userId}/`, { role: newRole });
      message.success('Role updated successfully');
      fetchUsers(); // Refresh user list
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Failed to update role';
      message.error(errorMsg);
    }
  };

  // Change user status
  const handleStatusChange = async (userId: string, newStatus: boolean) => {
    try {
      await api.patch(`/api/users/list/${userId}/`, { is_active: newStatus });
      message.success(`User ${newStatus ? 'enabled' : 'disabled'} successfully`);
      fetchUsers(); // Refresh user list
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || 'Failed to update status';
      message.error(errorMsg);
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role: string, record: User) => (
        <Select
          defaultValue={role}
          style={{ width: 120 }}
          onChange={(value) => handleRoleChange(record.id, value)}
          disabled={record.id === currentUser?.id} // Cannot change own role
        >
          <Option value='admin'>Admin</Option>
          <Option value='user'>User</Option>
          <Option value='analyst'>Analyst</Option>
        </Select>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>{isActive ? 'Active' : 'Inactive'}</Tag>
      ),
    },
    {
      title: 'Join Date',
      dataIndex: 'date_joined',
      key: 'date_joined',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: User) => (
        <Space size='middle'>
          {record.id !== currentUser?.id && ( // Cannot disable own account
            <Button
              type={record.is_active ? 'default' : 'primary'}
              onClick={() => handleStatusChange(record.id, !record.is_active)}
            >
              {record.is_active ? 'Disable' : 'Enable'}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card title='User Management'>
      <Table
        columns={columns}
        dataSource={users}
        rowKey='id'
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </Card>
  );
};

export default UserManagement;
