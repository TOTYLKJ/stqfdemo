import api from './config';
import { User } from '@/types';

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterCredentials {
  email: string;
  username: string;
  password: string;
  password2: string;
}

interface AuthResponse {
  user: User;
  access: string;
  refresh: string;
}

interface TokenResponse {
  access: string;
}

export const login = async (credentials: LoginCredentials): Promise<AuthResponse> => {
  const response = await api.post<AuthResponse>('/api/users/login/', credentials);
  console.log('API响应:', response);
  return response.data;
};

export const register = async (credentials: RegisterCredentials): Promise<AuthResponse> => {
  const response = await api.post<AuthResponse>('/api/users/register/', credentials);
  console.log('注册响应:', response);
  return response.data;
};

export const refreshToken = async (refresh: string): Promise<TokenResponse> => {
  const response = await api.post<TokenResponse>('/api/users/token/refresh/', { refresh });
  return response.data;
};

// 获取当前用户信息
export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get<User>('/api/users/me/');
  return response.data;
};
