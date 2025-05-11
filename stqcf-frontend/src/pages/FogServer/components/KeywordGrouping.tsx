import React, { useState } from 'react';
import { Button, Space, message } from 'antd';
import { GroupOutlined, SyncOutlined } from '@ant-design/icons';
import { triggerKeywordGrouping } from '@/api/fogServer';

interface KeywordGroupingProps {
  selectedServers: string[];
  onSuccess?: () => void;
}

const KeywordGrouping: React.FC<KeywordGroupingProps> = ({ selectedServers, onSuccess }) => {
  const [loading, setLoading] = useState(false);

  const handleGrouping = async () => {
    if (selectedServers.length === 0) {
      message.warning('Please select servers for keyword grouping');
      return;
    }

    setLoading(true);
    try {
      const result = await triggerKeywordGrouping(selectedServers);
      if (result.status === 'SUCCESS') {
        message.success('Keyword grouping completed');
        onSuccess?.();
      } else {
        message.error(result.error || 'Keyword grouping failed');
      }
    } catch (error) {
      console.error('Failed to trigger keyword grouping:', error);
      message.error('Failed to trigger keyword grouping');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Space direction='vertical' style={{ width: '100%' }}>
        <div>
          <h3>Keyword Grouping</h3>
          <p>Selected {selectedServers.length} servers</p>
        </div>
        <Button
          type='primary'
          icon={loading ? <SyncOutlined spin /> : <GroupOutlined />}
          onClick={handleGrouping}
          loading={loading}
          disabled={selectedServers.length === 0 || loading}
        >
          {loading ? 'Grouping in progress...' : 'Start Grouping'}
        </Button>
      </Space>
    </div>
  );
};

export default KeywordGrouping;
