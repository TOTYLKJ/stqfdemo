import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { refreshToken } from './auth';
import { message } from 'antd';

const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

console.log('API Base URL:', baseURL);

const api = axios.create({
  baseURL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log('Request Config:', {
      url: config.url,
      method: config.method,
      headers: config.headers,
    });
    return config;
  },
  (error: AxiosError) => {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log('Response:', {
      status: response.status,
      data: response.data,
    });
    return response;
  },
  async (error: AxiosError) => {
    console.error('Response Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
    });

    const originalRequest = error.config;

    if (error.response?.status === 401 && originalRequest) {
      // token过期，尝试刷新
      const refresh = localStorage.getItem('refresh_token');
      console.log('Token expired, attempting refresh...');

      if (refresh) {
        try {
          const response = await refreshToken(refresh);
          const { access } = response;
          console.log('Token refreshed successfully');

          // 更新token
          localStorage.setItem('token', access);

          // 重试原请求
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access}`;
          }
          return api(originalRequest);
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          // 刷新token失败，清除token并跳转到登录页
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        console.log('No refresh token found, redirecting to login');
        // 没有refresh token，直接跳转登录页
        window.location.href = '/login';
      }
    }

    // 其他错误处理
    if (error.response) {
      switch (error.response.status) {
        case 403:
          console.error('权限不足');
          break;
        case 404:
          console.error('请求的资源不存在');
          break;
        case 500:
          console.error('服务器错误');
          break;
        default:
          console.error(`请求失败: ${error.response.status}`);
      }
    } else if (error.request) {
      console.error('未收到响应:', error.request);
    } else {
      console.error('请求配置错误:', error.message);
    }

    return Promise.reject(error);
  }
);

export default api;
