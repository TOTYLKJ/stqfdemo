import api from './config';
import {
  FogServer,
  FogServerStatistics,
  FogServerFormData,
  KeywordGroupingResult,
} from '@/types/fogServer';

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// 获取雾服务器列表
export const getFogServers = async (params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<FogServer>> => {
  const response = await api.get('/api/fog-management/servers/', { params });
  return response.data;
};

// 获取雾服务器统计信息
export const getFogServerStats = async (): Promise<FogServerStatistics> => {
  const response = await api.get('/api/fog-management/servers/stats/');
  return response.data;
};

// 创建雾服务器
export const createFogServer = async (data: FogServerFormData): Promise<FogServer> => {
  const response = await api.post('/api/fog-management/servers/', data);
  return response.data;
};

// 更新雾服务器
export const updateFogServer = async (id: string, data: FogServerFormData): Promise<FogServer> => {
  const response = await api.put(`/api/fog-management/servers/${id}/`, data);
  return response.data;
};

// 删除雾服务器
export const deleteFogServer = async (id: string): Promise<void> => {
  await api.delete(`/api/fog-management/servers/${id}/`);
};

// 触发关键词分组
export const triggerKeywordGrouping = async (
  serverIds: string[]
): Promise<KeywordGroupingResult> => {
  const response = await api.post('/api/fog-management/servers/grouping/', {
    server_ids: serverIds,
    strategy: 'frequency_greedy',
  });
  return response.data;
};

// 获取任务状态
export const getTaskStatus = async (taskId: string): Promise<{ status: string }> => {
  const response = await api.get(`/api/fog-management/servers/task/${taskId}/`);
  return response.data;
};
