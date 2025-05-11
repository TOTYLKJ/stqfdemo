import api from './config';

export interface QueryRange {
  min_x: number;
  min_y: number;
  min_z: number;
  max_x: number;
  max_y: number;
  max_z: number;
}

export interface PointRange {
  lat_min: number;
  lon_min: number;
  time_min: number;
  lat_max: number;
  lon_max: number;
  time_max: number;
}

export interface MortonRange {
  min: string;
  max: string;
}

export interface QueryItem {
  keyword: number;
  morton_range?: MortonRange;
  grid_range?: QueryRange;
  point_range?: PointRange;
}

export interface QueryRequest {
  queries: QueryItem[];
  time_span: number;
  algorithm?: string;
}

export interface QueryResponse {
  status: string;
  data: {
    valid_trajectories: Array<
      Array<{
        decrypted_traj_id: string;
        decrypted_date: string;
        rid: string;
      }>
    >;
    total_count: number;
    steps?: Array<{
      step: string;
      details: {
        status?: 'success' | 'error' | 'warning';
        message?: string;
        [key: string]: any;
      };
      timestamp: string;
    }>;
  };
  message?: string;
  steps?: Array<{
    step: string;
    details: {
      status?: 'success' | 'error' | 'warning';
      message?: string;
      [key: string]: any;
    };
    timestamp: string;
  }>;
}

/**
 * 发送综合查询请求
 * @param queryData 查询参数
 * @returns 查询结果
 */
export const processQuery = async (queryData: QueryRequest): Promise<QueryResponse> => {
  try {
    // 根据算法选择API端点
    let apiEndpoint = '/api/query/process/';

    // 如果指定了算法，使用新的API端点
    if (queryData.algorithm) {
      if (queryData.algorithm === 'traversal') {
        apiEndpoint = '/api/query/api/trajectory/traversal';
      } else {
        apiEndpoint = '/api/query/api/trajectory';
      }
    }

    // 打印API基础URL和完整请求URL
    console.log('API基础URL:', process.env.REACT_APP_API_URL);
    console.log('完整请求URL:', `${process.env.REACT_APP_API_URL}${apiEndpoint}`);
    console.log('请求数据:', JSON.stringify(queryData, null, 2));

    // 使用选择的API端点发送请求
    const response = await api.post(apiEndpoint, queryData);

    console.log('响应数据:', response.data);

    // 确保响应数据格式正确
    if (response.data && response.data.status === 'success' && response.data.data) {
      // 确保valid_trajectories是一个数组
      if (!Array.isArray(response.data.data.valid_trajectories)) {
        response.data.data.valid_trajectories = [];
      }

      // 确保每个轨迹都有必要的字段
      response.data.data.valid_trajectories = response.data.data.valid_trajectories.map(
        (trajectoryGroup: any[]) => {
          if (!Array.isArray(trajectoryGroup)) {
            return [];
          }

          return trajectoryGroup.map((trajectory: any, index: number) => {
            if (!trajectory) {
              return {
                decrypted_traj_id: `traj_${index}`,
                decrypted_date: '未知日期',
                rid: `rid_${index}`,
              };
            }

            return {
              decrypted_traj_id: trajectory.decrypted_traj_id || `traj_${index}`,
              decrypted_date: trajectory.decrypted_date || '未知日期',
              rid: trajectory.rid || `rid_${index}`,
            };
          });
        }
      );
    }

    return response.data;
  } catch (error) {
    console.error('查询处理出错:', error);
    // 打印更详细的错误信息
    if (error.response) {
      console.error('错误状态码:', error.response.status);
      console.error('错误数据:', error.response.data);
      console.error('错误头信息:', error.response.headers);
    } else if (error.request) {
      console.error('未收到响应:', error.request);
    } else {
      console.error('错误信息:', error.message);
    }

    // 返回一个错误响应
    return {
      status: 'error',
      message: error.message || '查询处理失败',
      data: {
        valid_trajectories: [],
        total_count: 0,
      },
    };
  }
};

export default {
  processQuery,
};
