import React, { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Button, Space, message } from 'antd';
import { PlusOutlined, SyncOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import FogServerList from './components/FogServerList';
import FogServerForm from './components/FogServerForm';
import KeywordGrouping from './components/KeywordGrouping';
import FogServerStatistics from './components/FogServerStatistics';
import { FogServer } from '@/types/fogServer';
import { deleteFogServer } from '@/api/fogServer';
import styles from './index.module.css';

const FogServerPage: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingServer, setEditingServer] = useState<FogServer | null>(null);
  const [selectedServers, setSelectedServers] = useState<string[]>([]);
  const listRef = useRef<{ fetchServers: () => void }>();

  const handleAdd = () => {
    setEditingServer(null);
    setIsModalVisible(true);
  };

  const handleEdit = (server: FogServer) => {
    setEditingServer(server);
    setIsModalVisible(true);
  };

  const handleDelete = async (serverId: string) => {
    try {
      await deleteFogServer(serverId);
      message.success('Delete successful');
      listRef.current?.fetchServers();
    } catch (error) {
      message.error('Delete failed');
    }
  };

  const handleModalClose = () => {
    setIsModalVisible(false);
    setEditingServer(null);
    listRef.current?.fetchServers();
  };

  const handleSelectionChange = (selectedRowKeys: string[]) => {
    setSelectedServers(selectedRowKeys);
  };

  const handleRefresh = () => {
    listRef.current?.fetchServers();
  };

  return (
    <PageContainer>
      <Card className={styles.actionCard}>
        <Space>
          <Button type='primary' icon={<PlusOutlined />} onClick={handleAdd}>
            Add Server
          </Button>
          <Button icon={<SyncOutlined />} onClick={handleRefresh}>
            Refresh
          </Button>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <FogServerStatistics />
          </Card>
        </Col>
        <Col span={24}>
          <Card>
            <FogServerList
              ref={listRef}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onSelectionChange={handleSelectionChange}
            />
          </Card>
        </Col>
        <Col span={24}>
          <Card>
            <KeywordGrouping selectedServers={selectedServers} />
          </Card>
        </Col>
      </Row>

      <FogServerForm
        visible={isModalVisible}
        initialValues={editingServer}
        onClose={handleModalClose}
      />
    </PageContainer>
  );
};

export default FogServerPage;
