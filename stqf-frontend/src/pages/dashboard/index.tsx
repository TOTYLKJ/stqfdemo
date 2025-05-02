import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Spin,
  message,
  Table,
  Space,
  Modal,
  Form,
  Input,
} from 'antd';
import { SwapOutlined, EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import * as echarts from 'echarts';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '@/api/config';
import styles from './style.module.less';

// Fix Leaflet default icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

interface Statistics {
  total_points: number;
  total_keywords: number;
  keywords_list: string[];
}

interface TrackPoint {
  point_id: string;
  track_id: string;
  latitude: number;
  longitude: number;
  keyword: string;
  keywords: string[];
  date: number;
  time: number;
}

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<Statistics>({
    total_points: 0,
    total_keywords: 0,
    keywords_list: [],
  });
  const [showMap, setShowMap] = useState(false);
  const [trackPoints, setTrackPoints] = useState<TrackPoint[]>([]);
  const [selectedPoint, setSelectedPoint] = useState<TrackPoint | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const chartRef = useRef<HTMLDivElement>(null);
  const [mapConfig, setMapConfig] = useState({
    zoom: 4,
    center: [35.86166, 104.195397] as [number, number],
  });
  const [selectedMarker, setSelectedMarker] = useState<[number, number] | null>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [selectedRowKey, setSelectedRowKey] = useState<React.Key>();

  // Get statistics and track point data
  const fetchData = async (retryCount = 0) => {
    setLoading(true);
    try {
      // Check if token exists
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('Please login first');
        window.location.href = '/login';
        return;
      }

      console.log('Starting to fetch data...');

      // Parallel data requests to improve loading speed
      const [statsResponse, tracksResponse] = await Promise.all([
        api.get('/api/data-management/tracks/statistics/', {
          timeout: 60000,
        }),
        api.get('/api/data-management/tracks/', {
          timeout: 60000,
          params: {
            page: 1,
            page_size: 1000,
          },
        }),
      ]);

      console.log('API response data:', {
        statistics: statsResponse.data,
        tracks: tracksResponse.data,
      });

      // Validate data format
      if (!Array.isArray(tracksResponse.data.results)) {
        throw new Error('Track point data format error');
      }

      // Convert data format
      const validTrackPoints = tracksResponse.data.results.map((point: any) => {
        console.log('Original track point data:', point);
        return {
          point_id: point.point_id,
          track_id: point.track_id,
          latitude: Number(point.latitude),
          longitude: Number(point.longitude),
          keyword: point.keyword,
          keywords: Array.isArray(point.keywords) ? point.keywords : [point.keyword],
          date: point.date || 1,
          time: point.time || 1,
        };
      });

      console.log('Processed track point data:', validTrackPoints);
      setStatistics(statsResponse.data);
      setTrackPoints(validTrackPoints);
    } catch (error: any) {
      console.error('Failed to fetch data:', error);

      if ((error.code === 'ECONNABORTED' || error.message.includes('timeout')) && retryCount < 3) {
        console.log(`Retry ${retryCount + 1}...`);
        message.warning(`Request timeout, retrying (${retryCount + 1}/3)...`);
        await new Promise((resolve) => setTimeout(resolve, 2000));
        return fetchData(retryCount + 1);
      }

      if (error.response) {
        console.error('Error response:', {
          status: error.response.status,
          data: error.response.data,
          headers: error.response.headers,
        });

        switch (error.response.status) {
          case 401:
            message.error('Login expired, please login again');
            window.location.href = '/login';
            break;
          case 403:
            message.error('No access permission');
            break;
          case 404:
            message.error('Requested resource does not exist');
            break;
          case 500:
            message.error('Server error, please try again later');
            break;
          default:
            message.error(
              error.response.data?.error ||
                error.response.data?.detail ||
                'Failed to fetch data, please try again later'
            );
        }
      } else if (error.code === 'ECONNABORTED') {
        console.error('Request timeout');
        message.error('Request timeout, please check network connection or contact administrator');
      } else if (error.request) {
        console.error('No response received:', error.request);
        message.error('Unable to connect to server, please check network connection');
      } else {
        console.error('Request configuration error:', error.message);
        message.error('Request configuration error, please contact administrator');
      }
    } finally {
      setLoading(false);
    }
  };

  // Clean up chart instance
  const cleanupChart = useCallback(() => {
    if (chartInstance.current) {
      chartInstance.current.dispose();
      chartInstance.current = null;
    }
  }, []);

  // Initialize chart
  const initChart = useCallback(() => {
    if (!chartRef.current || !trackPoints.length) return;

    cleanupChart();

    setTimeout(() => {
      if (!chartRef.current) return;
      const chart = echarts.init(chartRef.current);
      chartInstance.current = chart;

      const keywordCounts: { [key: string]: number } = {};
      trackPoints.forEach((point) => {
        if (point.keyword) {
          keywordCounts[point.keyword] = (keywordCounts[point.keyword] || 0) + 1;
        }
      });

      const option = {
        title: {
          text: 'Keyword Frequency Statistics',
          left: 'center',
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow',
          },
        },
        grid: {
          top: 60,
          right: 20,
          bottom: 60,
          left: 30,
          containLabel: true,
        },
        xAxis: {
          type: 'category',
          data: Object.keys(keywordCounts),
          axisLabel: {
            rotate: 45,
            interval: 0,
          },
        },
        yAxis: {
          type: 'value',
          name: 'Frequency',
        },
        series: [
          {
            name: 'Occurrences',
            type: 'bar',
            data: Object.values(keywordCounts),
            itemStyle: {
              color: '#1890ff',
            },
          },
        ],
      };

      chart.setOption(option);
    }, 100);
  }, [trackPoints, cleanupChart]);

  // Display track point on map
  const showPointOnMap = useCallback((point: TrackPoint) => {
    try {
      setSelectedMarker([point.latitude, point.longitude]);
      setMapConfig({
        zoom: 13,
        center: [point.latitude, point.longitude],
      });
      message.success(`Track point displayed on map: ${point.point_id}`);
    } catch (error) {
      console.error('Error displaying track point:', error);
      message.error('Failed to display track point');
    }
  }, []);

  // Switch view
  const toggleView = useCallback(() => {
    const newShowMap = !showMap;
    if (newShowMap) {
      // Clean up chart when switching to map view
      cleanupChart();
    } else {
      // Clean up map-related state when switching to chart view
      setSelectedMarker(null);
      setSelectedPoint(null);
      setSelectedRowKey(undefined);
    }
    setShowMap(newShowMap);
  }, [showMap, cleanupChart]);

  // Chart initialization
  useEffect(() => {
    if (!showMap && trackPoints.length > 0 && !loading) {
      // Ensure chart is initialized in next render cycle
      setTimeout(() => {
        initChart();
      }, 0);
    }
  }, [showMap, trackPoints, loading, initChart]);

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      cleanupChart();
    };
  }, [cleanupChart]);

  // Add selection change handler
  const onSelectChange = useCallback(
    (selectedKey: React.Key) => {
      if (!selectedKey) {
        console.warn('Selected track point ID is invalid:', selectedKey);
        return;
      }

      try {
        // Find selected track point
        const selectedPoint = trackPoints.find((point) => point.point_id === selectedKey);
        if (!selectedPoint) {
          throw new Error('Selected track point not found');
        }

        setSelectedRowKey(selectedKey);
        setSelectedPoint(selectedPoint);
        message.success(`Track point selected: ${selectedPoint.point_id}`);
      } catch (error) {
        console.error('Failed to get track point details:', error);
        message.error('Failed to get track point details');
        setSelectedPoint(null);
        setSelectedRowKey(undefined);
      }
    },
    [trackPoints]
  );

  // Modify table column definitions
  const columns = [
    {
      title: 'Point ID',
      dataIndex: 'point_id',
      key: 'point_id',
    },
    {
      title: 'Track ID',
      dataIndex: 'track_id',
      key: 'track_id',
    },
    {
      title: 'Latitude',
      dataIndex: 'latitude',
      key: 'latitude',
    },
    {
      title: 'Longitude',
      dataIndex: 'longitude',
      key: 'longitude',
    },
    {
      title: 'Keyword',
      dataIndex: 'keyword',
      key: 'keyword',
    },
    {
      title: 'Actions',
      key: 'action',
      render: (_: any, record: TrackPoint) => {
        const isSelected = selectedRowKey === record.point_id;
        return (
          <Space size='middle'>
            <Button
              type={isSelected ? 'primary' : 'text'}
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            >
              Edit
            </Button>
            <Button
              type={isSelected ? 'primary' : 'text'}
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.point_id)}
            >
              Delete
            </Button>
            {isSelected && showMap && (
              <Button type='primary' onClick={() => showPointOnMap(record)}>
                Show on Map
              </Button>
            )}
          </Space>
        );
      },
    },
  ];

  // Single selection configuration
  const rowSelection = {
    type: 'radio' as const,
    selectedRowKeys: selectedRowKey ? [selectedRowKey] : [],
    onChange: (selectedRowKeys: React.Key[]) => {
      if (!selectedRowKeys.length) {
        return;
      }
      const selectedKey = selectedRowKeys[0];
      console.log('Selected track point ID:', selectedKey);
      onSelectChange(selectedKey);
    },
  };

  // Modify handleEdit function
  const handleEdit = (record: TrackPoint) => {
    if (selectedRowKey !== record.point_id) {
      message.warning('Please select a track point to edit');
      return;
    }
    console.log('Edit track point:', record);
    setSelectedPoint(record);
    form.setFieldsValue({
      track_id: record.track_id,
      latitude: record.latitude,
      longitude: record.longitude,
      keyword: record.keyword,
      date: record.date || 1,
      time: record.time || 1,
    });
    setIsModalVisible(true);
  };

  // Modify handleDelete function
  const handleDelete = async (point_id: string) => {
    if (selectedRowKey !== point_id) {
      message.warning('Please select a track point to delete');
      return;
    }
    try {
      await api.delete(`/api/data-management/tracks/${point_id}/`);
      message.success('Delete successful');
      setSelectedRowKey(undefined);
      setSelectedPoint(null);
      fetchData();
    } catch (error) {
      message.error('Delete failed');
      console.error('Delete failed:', error);
    }
  };

  // Handle save
  const handleSave = async (values: any) => {
    try {
      console.log('Save track point:', { selectedPoint, values });

      // Validate latitude and longitude range
      const latitude = Number(values.latitude);
      const longitude = Number(values.longitude);
      if (latitude < -90 || latitude > 90) {
        message.error('Latitude must be between -90 and 90 degrees');
        return;
      }
      if (longitude < -180 || longitude > 180) {
        message.error('Longitude must be between -180 and 180 degrees');
        return;
      }

      const data = {
        track_id: values.track_id,
        point_id: selectedPoint ? selectedPoint.point_id : `${values.track_id}_p000001`,
        latitude: latitude,
        longitude: longitude,
        keyword: values.keyword,
        keywords: [values.keyword], // Ensure keywords field is an array
        date: Number(values.date) || 1,
        time: Number(values.time) || 1,
      };

      let response;
      if (selectedPoint?.point_id) {
        // Edit existing track point
        console.log('Edit track point:', selectedPoint.point_id);
        try {
          response = await api.put(`/api/data-management/tracks/${selectedPoint.point_id}/`, data);
          console.log('Update response:', response);
          if (response.data) {
            setSelectedPoint(response.data);
            message.success('Update successful');
          }
        } catch (error: any) {
          if (error.response?.status === 404) {
            message.error('Track point does not exist, may have been deleted');
            return;
          }
          throw error;
        }
      } else {
        // Add new track point
        console.log('Add new track point');
        response = await api.post('/api/data-management/tracks/', data);
        console.log('Create response:', response);
        if (response.data) {
          setSelectedPoint(response.data);
          message.success('Add successful');
        }
      }

      setIsModalVisible(false);
      form.resetFields();
      setSelectedPoint(null);
      await fetchData(); // Refresh data
    } catch (error: any) {
      console.error('Save failed:', error);
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Save failed, please try again';
      message.error(errorMessage);
    }
  };

  // Initialization
  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className={styles.dashboard}>
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card>
            <Statistic
              title='Total Track Points'
              value={statistics.total_points}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <Statistic title='Total Keywords' value={statistics.total_keywords} loading={loading} />
          </Card>
        </Col>
      </Row>

      <Row justify='center' style={{ margin: '16px 0' }}>
        <Button type='primary' icon={<SwapOutlined />} onClick={toggleView}>
          Switch to {showMap ? 'Bar Chart' : 'Map'} View
        </Button>
      </Row>

      <Card style={{ marginTop: 16 }}>
        {loading ? (
          <div className={styles.loadingContainer}>
            <Spin size='large' tip='Loading...' />
          </div>
        ) : (
          <div className={styles.visualContainer}>
            <div style={{ display: showMap ? 'none' : 'block' }}>
              <div
                ref={chartRef}
                style={{
                  height: '400px',
                  width: '100%',
                  position: 'relative',
                }}
                className={styles.chartContainer}
              />
            </div>
            <div style={{ display: showMap ? 'block' : 'none', height: '400px' }}>
              <MapContainer
                center={mapConfig.center}
                zoom={mapConfig.zoom}
                style={{ height: '100%', width: '100%' }}
                key={`map-${selectedMarker ? 'with-marker' : 'no-marker'}`}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
                />
                {selectedMarker && selectedPoint && (
                  <Marker position={selectedMarker}>
                    <Popup>Keyword: {selectedPoint.keyword}</Popup>
                  </Marker>
                )}
              </MapContainer>
            </div>
          </div>
        )}
      </Card>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title='Track Point Management'>
            <Table
              rowSelection={rowSelection}
              columns={columns}
              dataSource={trackPoints}
              rowKey='point_id'
              loading={loading}
              onRow={(record: TrackPoint) => ({
                onClick: () => {
                  console.log('Clicked row, track point ID:', record.point_id);
                  onSelectChange(record.point_id);
                },
              })}
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title={selectedPoint ? 'Edit Track Point' : 'Add Track Point'}
        open={isModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
          setSelectedPoint(null);
        }}
      >
        <Form form={form} layout='vertical' onFinish={handleSave}>
          <Form.Item
            name='track_id'
            label='Track ID'
            rules={[{ required: true, message: 'Please enter track ID' }]}
          >
            <Input disabled={!!selectedPoint} placeholder='Please enter track ID' />
          </Form.Item>
          <Form.Item
            name='latitude'
            label='Latitude'
            rules={[
              { required: true, message: 'Please enter latitude' },
              {
                type: 'number',
                min: -90,
                max: 90,
                message: 'Latitude must be between -90 and 90 degrees',
              },
            ]}
          >
            <Input type='number' placeholder='Please enter latitude' />
          </Form.Item>
          <Form.Item
            name='longitude'
            label='Longitude'
            rules={[
              { required: true, message: 'Please enter longitude' },
              {
                type: 'number',
                min: -180,
                max: 180,
                message: 'Longitude must be between -180 and 180 degrees',
              },
            ]}
          >
            <Input type='number' placeholder='Please enter longitude' />
          </Form.Item>
          <Form.Item
            name='keyword'
            label='Keyword'
            rules={[{ required: true, message: 'Please enter keyword' }]}
          >
            <Input placeholder='Please enter keyword' />
          </Form.Item>
          <Form.Item
            name='date'
            label='Date'
            rules={[{ required: true, message: 'Please enter date' }]}
          >
            <Input type='number' placeholder='Please enter date' />
          </Form.Item>
          <Form.Item
            name='time'
            label='Time'
            rules={[{ required: true, message: 'Please enter time' }]}
          >
            <Input type='number' placeholder='Please enter time' />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Dashboard;
