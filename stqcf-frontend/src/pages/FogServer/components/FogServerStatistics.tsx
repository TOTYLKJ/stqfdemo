import React, { useEffect, useState } from 'react';
import { Row, Col, Statistic, Card } from 'antd';
import {
  CloudServerOutlined,
  ApiOutlined,
  LoadingOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { FogServerStatistics as Stats } from '@/types/fogServer';
import { getFogServerStats } from '@/api/fogServer';

const FogServerStatistics: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats>({
    total_servers: 0,
    online_servers: 0,
    total_keywords: 0,
    average_load: 0,
  });

  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await getFogServerStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Refresh statistics every 30 seconds
    const timer = setInterval(fetchStats, 30000);
    return () => clearInterval(timer);
  }, []);

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title='Total Servers'
            value={stats.total_servers}
            prefix={<CloudServerOutlined />}
            loading={loading}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title='Online Servers'
            value={stats.online_servers}
            prefix={<ApiOutlined />}
            loading={loading}
            valueStyle={{ color: '#3f8600' }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title='Total Keywords'
            value={stats.total_keywords}
            prefix={<BarChartOutlined />}
            loading={loading}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card>
          <Statistic
            title='Average Load'
            value={stats.average_load}
            prefix={<LoadingOutlined />}
            loading={loading}
            precision={2}
            suffix='%'
          />
        </Card>
      </Col>
    </Row>
  );
};

export default FogServerStatistics;
