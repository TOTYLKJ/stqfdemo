import api from './config';

export interface TrackData {
  track_id: string;
  point_id: string;
  latitude: number;
  longitude: number;
  date: number;
  time: number;
  keyword: string;
}

export interface Statistics {
  total_points: number;
  total_keywords: number;
  keywords_list: string[];
}

export interface TrackResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: TrackData[];
}

// 获取轨迹数据列表
export const getTracks = async (params: {
  page: number;
  page_size?: number;
  keyword?: string;
  date_start?: string;
  date_end?: string;
}): Promise<TrackResponse> => {
  const response = await api.get('/api/data-management/tracks/', { params });
  return response.data;
};

// 获取统计信息
export const getStatistics = async (): Promise<Statistics> => {
  const response = await api.get('/api/data-management/tracks/statistics/');
  return response.data;
};

// 导出 CSV
export const exportCSV = async (): Promise<Blob> => {
  const response = await api.get('/api/data-management/tracks/export_csv/', {
    responseType: 'blob',
  });
  return response.data;
};

// 导出 JSON
export const exportJSON = async (): Promise<Blob> => {
  const response = await api.get('/api/data-management/tracks/export_json/', {
    responseType: 'blob',
  });
  return response.data;
};
