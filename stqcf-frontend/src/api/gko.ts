import axios from 'axios';
import { message } from 'antd';

const API_URL = process.env.REACT_APP_API_URL || '';

/**
 * 构建八叉树索引
 * 调用后端API触发八叉树数据迁移
 */
export const buildTreeIndex = async () => {
  try {
    // 获取token
    const token = localStorage.getItem('token');

    // 发送请求
    const response = await axios.post(
      `${API_URL}/api/data-management/octree/migration/`, // 使用新的API端点
      { confirm: true }, // 请求体包含confirm参数
      {
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '', // 添加Authorization头
        },
      }
    );

    console.log('API响应:', response.data);

    return {
      success: response.data.status === 'success',
      message: response.data.message,
    };
  } catch (error) {
    console.error('构建树索引时出错:', error);
    if (error.response) {
      console.error('错误响应状态:', error.response.status);
      console.error('错误响应数据:', error.response.data);
    }

    return {
      success: false,
      message: error.response?.data?.message || error.message || '未知错误',
    };
  }
};

/**
 * 分配轨迹点
 * 调用后端process_trajectory_data.py脚本
 */
export const distributeTrajectoryPoints = async () => {
  try {
    // 获取token
    const token = localStorage.getItem('token');

    // 发送请求
    const response = await axios.post(
      `${API_URL}/api/data-management/trajectory/migration/`,
      { confirm: true },
      {
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '', // 添加Authorization头
        },
      }
    );

    console.log('API响应:', response.data);

    return {
      success: response.data.status === 'success',
      message: response.data.message,
    };
  } catch (error) {
    console.error('分配轨迹点时出错:', error);
    if (error.response) {
      console.error('错误响应状态:', error.response.status);
      console.error('错误响应数据:', error.response.data);
    }

    return {
      success: false,
      message: error.response?.data?.message || error.message || '未知错误',
    };
  }
};

/**
 * 获取八叉树节点数据
 * 用于可视化展示
 */
export const getOctreeNodes = async () => {
  try {
    const response = await axios.get(`${API_URL}/api/gko/octree-nodes`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return response.data;
  } catch (error) {
    console.error('获取八叉树节点数据时出错:', error);
    throw error;
  }
};

/**
 * 触发八叉树数据迁移
 * 调用后端八叉树数据迁移API
 */
export const migrateOctreeData = async () => {
  try {
    // 获取token
    const token = localStorage.getItem('token');

    // 发送请求
    const response = await axios.post(
      `${API_URL}/api/data-management/octree/migration/`, // 使用新的API端点
      {
        confirm: true, // 请求体包含confirm参数
      },
      {
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '', // 添加Authorization头
        },
      }
    );
    return {
      success: response.data.status === 'success',
      message: response.data.message,
    };
  } catch (error) {
    console.error('八叉树数据迁移时出错:', error);
    if (error.response) {
      console.error('错误响应状态:', error.response.status);
      console.error('错误响应数据:', error.response.data);
    }
    return {
      success: false,
      message: error.response?.data?.message || error.message || '未知错误',
    };
  }
};

/**
 * 测试API连接
 */
export const testApiConnection = async () => {
  try {
    console.log('测试API连接...');
    console.log('API_URL:', API_URL);

    const response = await axios.get(`${API_URL}/api/test/`);
    console.log('测试API响应:', response.data);

    return {
      success: true,
      message: '连接成功',
      data: response.data,
    };
  } catch (error) {
    console.error('测试API连接失败:', error);
    if (error.response) {
      console.error('错误响应状态:', error.response.status);
      console.error('错误响应数据:', error.response.data);
    }

    return {
      success: false,
      message: error.message || '连接失败',
      error: error,
    };
  }
};

export default {
  buildTreeIndex,
  distributeTrajectoryPoints,
  getOctreeNodes,
  migrateOctreeData,
  testApiConnection,
};
