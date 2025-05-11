import React, { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import Layout from '@components/Layout';
import PrivateRoute from '@components/PrivateRoute';
import { CloudServerOutlined, AppstoreOutlined, SafetyOutlined } from '@ant-design/icons';

// 懒加载路由组件
const Login = lazy(() => import('@pages/auth/Login'));
const Register = lazy(() => import('@pages/auth/Register'));
const Dashboard = lazy(() => import('@pages/dashboard'));
const DataMaintenance = lazy(() => import('@pages/DataMaintenance'));
const MapQuery = lazy(() => import('@pages/map'));
const Monitor = lazy(() => import('@pages/monitor'));
const Profile = lazy(() => import('@pages/profile'));
const UserManagement = lazy(() => import('@pages/settings/UserManagement'));
const FogServer = lazy(() => import('@pages/FogServer'));
const GKO = lazy(() => import('@pages/GKO'));
const SafeQuery = lazy(() => import('@pages/safe'));

const LoadingComponent = () => <div>Loading...</div>;

// 定义菜单配置（用于Layout组件中的菜单渲染）
export const menuConfig = [
  {
    path: '/fog',
    icon: <CloudServerOutlined />,
    name: '雾服务器管理',
  },
  {
    path: '/gko',
    icon: <AppstoreOutlined />,
    name: 'GKO管理',
  },
  {
    path: '/safe',
    icon: <SafetyOutlined />,
    name: '安全查询',
  },
  // ... 其他菜单项
];

const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <PrivateRoute>
        <Layout />
      </PrivateRoute>
    ),
    children: [
      {
        path: '/',
        element: <Navigate to='/dashboard' replace />,
      },
      {
        path: 'dashboard',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <Dashboard />
          </Suspense>
        ),
      },
      {
        path: 'data-maintenance',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <DataMaintenance />
          </Suspense>
        ),
      },
      {
        path: 'map',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <MapQuery />
          </Suspense>
        ),
      },
      {
        path: 'monitor',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <Monitor />
          </Suspense>
        ),
      },
      {
        path: 'profile',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <Profile />
          </Suspense>
        ),
      },
      {
        path: 'settings/user-management',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <UserManagement />
          </Suspense>
        ),
      },
      {
        path: 'fog',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <FogServer />
          </Suspense>
        ),
      },
      {
        path: 'gko',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <GKO />
          </Suspense>
        ),
      },
      {
        path: 'safe',
        element: (
          <Suspense fallback={<LoadingComponent />}>
            <SafeQuery />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: '/login',
    element: (
      <Suspense fallback={<LoadingComponent />}>
        <Login />
      </Suspense>
    ),
  },
  {
    path: '/register',
    element: (
      <Suspense fallback={<LoadingComponent />}>
        <Register />
      </Suspense>
    ),
  },
]);

export default router;
