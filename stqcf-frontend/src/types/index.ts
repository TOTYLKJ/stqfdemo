// 用户相关类型
export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user' | 'operator';
  created_at: string;
  last_login: string;
}

// 认证相关类型
export interface AuthState {
  user: User | null;
  token: string | null;
  refresh_token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

// 轨迹查询相关类型
export interface TrajectoryQuery {
  lon_min: number;
  lat_min: number;
  lon_max: number;
  lat_max: number;
  time_start: string;
  time_end: string;
  keywords: string[];
}

export interface TrajectoryResult {
  id: string;
  trajectory_id: string;
  time_range: {
    start: string;
    end: string;
  };
  keywords: string[];
  grid_cells: {
    lon: number;
    lat: number;
    count: number;
  }[];
}

// 系统监控相关类型
export interface ServerStatus {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'warning';
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  last_updated: string;
}

export interface QueryLog {
  id: string;
  user_id: string;
  query_type: string;
  query_params: TrajectoryQuery;
  result_count: number;
  execution_time: number;
  timestamp: string;
}
