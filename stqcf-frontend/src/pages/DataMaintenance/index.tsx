import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  DatePicker,
  Input,
  Space,
  message,
  Statistic,
  Progress,
  List,
} from 'antd';
import { InboxOutlined, DownloadOutlined, SearchOutlined } from '@ant-design/icons';
import { Upload, Button } from 'antd';
import type { UploadProps } from 'antd';
import dayjs from 'dayjs';
import debounce from 'lodash/debounce';
import './style.css';
import {
  getTracks,
  getStatistics,
  exportCSV,
  exportJSON,
  TrackData,
  Statistics,
} from '../../api/tracks';
import api from '../../api/config';
import enUS from 'antd/lib/locale/en_US';
import { ConfigProvider } from 'antd';

const { RangePicker } = DatePicker;
const { Dragger } = Upload;

const DataMaintenance = () => {
  const [trackData, setTrackData] = useState<TrackData[]>([]);
  const [statistics, setStatistics] = useState<Statistics>({
    total_points: 0,
    total_keywords: 0,
    keywords_list: [],
  });
  const [loading, setLoading] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([
    null,
    null,
  ]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // Use debounce to optimize statistics fetching
  const fetchStatistics = useCallback(
    debounce(async () => {
      try {
        const data = await getStatistics();
        setStatistics(data);
      } catch (error) {
        message.error('Failed to fetch statistics');
      }
    }, 5000), // 5 seconds debounce
    []
  );

  // Fetch track data function now supports pagination
  const fetchTrackData = async (pageNum = 1, append = false) => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const params: any = {
        page: pageNum,
        page_size: 50,
      };

      if (searchKeyword) {
        params.keyword = searchKeyword;
      }
      if (dateRange[0] && dateRange[1]) {
        params.date_start = dateRange[0].format('YYYYMMDD');
        params.date_end = dateRange[1].format('YYYYMMDD');
      }

      const data = await getTracks(params);

      if (append) {
        setTrackData((prev) => [...prev, ...data.results]);
      } else {
        setTrackData(data.results);
      }

      setHasMore(data.next !== null);
      setPage(pageNum);
    } catch (error) {
      message.error('Failed to fetch track data');
    } finally {
      setLoadingMore(false);
      setLoading(false);
    }
  };

  // Modified query function type
  const handleSearch = () => {
    setPage(1);
    setHasMore(true);
    setTrackData([]);
    fetchTrackData(1, false);
  };

  // Initial loading
  useEffect(() => {
    fetchTrackData(1, false);
    fetchStatistics();
  }, []);

  // File upload configuration
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.csv',
    action: `${api.defaults.baseURL}/api/data-management/tracks/import_csv/`,
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    beforeUpload: (file) => {
      // Check file type
      if (!file.name.endsWith('.csv')) {
        message.error('Only CSV files can be uploaded!');
        return false;
      }

      // Check file size (limit to 100MB)
      const isLt100M = file.size / 1024 / 1024 < 100;
      if (!isLt100M) {
        message.error('File must be smaller than 100MB!');
        return false;
      }

      // Read the first line of the CSV file to validate format
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const firstLine = text.split('\n')[0];
        const expectedHeaders = ['tID', 'latitude', 'longitude', 'keyword', 'date', 'time'];
        const headers = firstLine.trim().split(',');

        const missingHeaders = expectedHeaders.filter((header) => !headers.includes(header));
        if (missingHeaders.length > 0) {
          message.error(
            `CSV file format error! Missing required columns: ${missingHeaders.join(', ')}`
          );
          return false;
        }
      };
      reader.readAsText(file);

      return true;
    },
    onChange(info) {
      const { status, response } = info.file;
      if (status === 'uploading') {
        setUploading(true);
        if (info.file.percent) {
          setUploadProgress(Math.round(info.file.percent));
        }
      } else if (status === 'done') {
        setUploading(false);
        setUploadProgress(0);
        message.success(`${info.file.name} uploaded successfully, imported ${response.message}`);
        fetchStatistics();
        fetchTrackData();
      } else if (status === 'error') {
        setUploading(false);
        setUploadProgress(0);
        const errorMsg = response?.error || 'File upload failed';
        message.error(`${info.file.name} ${errorMsg}`);
      }
    },
    onDrop(e) {
      console.log('Dropped files', e.dataTransfer.files);
    },
    showUploadList: false,
  };

  // Export CSV
  const handleExportCSV = async () => {
    try {
      const blob = await exportCSV();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'tracks.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success('Export successful');
    } catch (error) {
      message.error('Export failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  // Export JSON
  const handleExportJSON = async () => {
    try {
      const blob = await exportJSON();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'tracks.json';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      message.success('Export successful');
    } catch (error) {
      message.error('Export failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  return (
    <div className='data-maintenance'>
      <Row gutter={[16, 16]}>
        {/* Data Import/Export Area */}
        <Col span={12}>
          <Card title='Data Import' className='import-card'>
            <Dragger {...uploadProps}>
              <p className='ant-upload-drag-icon'>
                <InboxOutlined />
              </p>
              <p className='ant-upload-text'>Click or drag file to this area to upload</p>
              <p className='ant-upload-hint'>
                Supports single CSV file upload, file size no more than 100MB
                <br />
                CSV file must include the following columns: tID, latitude, longitude, keyword,
                date, time
              </p>
            </Dragger>
            {uploading && (
              <div style={{ marginTop: 16 }}>
                <Progress
                  percent={uploadProgress}
                  status={uploadProgress === 100 ? 'success' : 'active'}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
              </div>
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title='Data Export' className='export-card'>
            <Space direction='vertical' style={{ width: '100%' }}>
              <Button type='primary' icon={<DownloadOutlined />} block onClick={handleExportCSV}>
                Export as CSV
              </Button>
              <Button icon={<DownloadOutlined />} block onClick={handleExportJSON}>
                Export as JSON
              </Button>
            </Space>
          </Card>
        </Col>

        {/* Track List Area */}
        <Col span={6}>
          <Card className='statistics-card'>
            <Statistic title='Total Track Points' value={statistics.total_points} />
            <Statistic title='Total Keywords' value={statistics.total_keywords} />
          </Card>
        </Col>
        <Col span={18}>
          <Card className='track-list-card'>
            <Space style={{ marginBottom: 16 }}>
              <ConfigProvider locale={enUS}>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
                />
              </ConfigProvider>
              <Input
                placeholder='Search keyword'
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                prefix={<SearchOutlined />}
              />
              <Button type='primary' onClick={handleSearch}>
                Search
              </Button>
            </Space>
            <List
              loading={loading}
              dataSource={trackData}
              renderItem={(item: TrackData) => (
                <List.Item>
                  <Row style={{ width: '100%' }}>
                    <Col span={4}>{item.track_id}</Col>
                    <Col span={4}>{item.point_id}</Col>
                    <Col span={4}>{item.latitude}</Col>
                    <Col span={4}>{item.longitude}</Col>
                    <Col span={4}>{item.date}</Col>
                    <Col span={4}>{item.keyword}</Col>
                  </Row>
                </List.Item>
              )}
              loadMore={
                hasMore && (
                  <div style={{ textAlign: 'center', marginTop: 12, height: 32 }}>
                    <Button loading={loadingMore} onClick={() => fetchTrackData(page + 1, true)}>
                      Load More
                    </Button>
                  </div>
                )
              }
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default DataMaintenance;
