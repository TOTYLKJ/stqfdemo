import React from 'react';
import { Layout, Menu, Dropdown, Space, Avatar } from 'antd';
import type { MenuProps } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  DashboardOutlined,
  SafetyCertificateOutlined,
  MonitorOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { logout } from '@/store/slices/authSlice';
import { RootState } from '@/store';
import Logo from '@/components/Logo';
import './style.css';

const { Header, Sider, Content } = Layout;

const AppLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const { user } = useSelector((state: RootState) => state.auth);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  const userMenu: MenuProps = {
    items: [
      {
        key: 'profile',
        icon: <UserOutlined />,
        label: 'Profile',
        onClick: () => navigate('/profile'),
      },
      {
        type: 'divider',
      },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: 'Logout',
        onClick: handleLogout,
      },
    ],
  };

  const getMenuItems = () => {
    const items: MenuProps['items'] = [];

    if (user?.role === 'admin') {
      items.push({
        key: 'data-management',
        icon: <DashboardOutlined />,
        label: 'Data Management',
        children: [
          {
            key: 'data-maintenance',
            label: 'Data Maintenance',
            onClick: () => navigate('/data-maintenance'),
          },
          {
            key: 'dashboard',
            label: 'Visualization Analysis',
            onClick: () => navigate('/dashboard'),
          },
        ],
      });
    }

    items.push(
      {
        key: 'data-processing',
        icon: <SafetyCertificateOutlined />,
        label: 'Data Processing',
        children: [
          {
            key: 'gko-tree',
            label: 'GKO Tree Construction',
          },
          {
            key: 'fog-server',
            label: 'Fog Server Management',
          },
        ],
      },
      {
        key: 'data-query',
        icon: <MonitorOutlined />,
        label: 'Data Query',
        children: [
          {
            key: 'safe-range-query',
            label: 'Safe Range Query',
          },
        ],
      },
      {
        key: 'monitor',
        icon: <MonitorOutlined />,
        label: 'System Monitoring',
        children: [
          {
            key: 'system-status',
            label: 'System Status',
          },
          {
            key: 'operation-log',
            label: 'Operation Log',
          },
        ],
      }
    );

    if (user?.role === 'admin') {
      items.push({
        key: 'settings',
        icon: <SettingOutlined />,
        label: 'System Settings',
        children: [
          {
            key: 'user-management',
            label: 'User Management',
            onClick: () => navigate('/settings/user-management'),
          },
          {
            key: 'system-config',
            label: 'System Configuration',
          },
        ],
      });
    }

    return items;
  };

  const handleMenuClick = ({ key }: { key: string }) => {
    if (key === 'user-management' || key === 'data-maintenance') {
      return;
    }
    const mainRoute = key.split('-')[0];
    navigate(`/${mainRoute}`);
  };

  return (
    <Layout className='app-layout'>
      <Header className='app-header'>
        <Logo />
        <div className='header-right'>
          <Dropdown menu={userMenu} placement='bottomRight' trigger={['click']}>
            <Space className='user-info'>
              <Avatar icon={<UserOutlined />} />
              <span className='username'>{user?.username || 'User'}</span>
            </Space>
          </Dropdown>
        </div>
      </Header>
      <Layout>
        <Sider width={240} className='app-sider'>
          <Menu
            mode='inline'
            selectedKeys={[
              location.pathname.split('/')[2] || location.pathname.split('/')[1] || 'dashboard',
            ]}
            defaultOpenKeys={[
              'data-management',
              'data-processing',
              'data-query',
              'monitor',
              'settings',
            ]}
            style={{ height: '100%', borderRight: 0 }}
            items={getMenuItems()}
            onClick={handleMenuClick}
          />
        </Sider>
        <Layout className='main-content'>
          <Content className='content'>
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
