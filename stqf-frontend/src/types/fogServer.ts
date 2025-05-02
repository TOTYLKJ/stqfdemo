export interface FogServer {
  id: string;
  service_endpoint: string;
  keywords: string[] | string;
  keyword_load: number;
  status: 'online' | 'offline' | 'maintenance';
  created_at: string;
  updated_at: string;
}

export interface FogServerStatistics {
  total_servers: number;
  online_servers: number;
  total_keywords: number;
  average_load: number;
}

export interface FogServerFormData {
  service_endpoint: string;
  status: 'online' | 'offline' | 'maintenance';
}

export interface KeywordGroupingResult {
  status: string;
  message?: string;
  error?: string;
}
