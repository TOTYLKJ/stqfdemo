import React from 'react';
import { Modal, Timeline, Badge, Typography, Spin, Empty, Tag } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  LoadingOutlined,
  CloudOutlined,
  ClusterOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

// Step details interface
export interface StepDetail {
  status?: 'success' | 'error' | 'warning';
  message?: string;
  results_count?: number;
  trajectories_count?: number;
  valid_trajectories_count?: number;
  [key: string]: any;
}

// Step interface
export interface QueryStep {
  step: string;
  details: StepDetail;
  timestamp: string;
}

// Component props interface
interface QueryStepsModalProps {
  visible: boolean;
  onClose: () => void;
  steps: QueryStep[];
  loading?: boolean;
  queryId?: string;
}

// Get status icon
const getStatusIcon = (status?: string) => {
  switch (status) {
    case 'success':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    case 'error':
      return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
    case 'warning':
      return <WarningOutlined style={{ color: '#faad14' }} />;
    default:
      return <LoadingOutlined style={{ color: '#1890ff' }} />;
  }
};

// Format timestamp
const formatTimestamp = (timestamp: string) => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour12: false });
  } catch (error) {
    return timestamp;
  }
};

// Get server type tag
const getServerTypeTag = (step: string, details: StepDetail) => {
  // Determine server type based on step name and details
  if (step.includes('Fog Server') || step.includes('雾服务器') || details.fog_server) {
    return (
      <Tag icon={<ClusterOutlined />} color='purple'>
        Fog Server
      </Tag>
    );
  }
  if (
    step.includes('STV Validation') ||
    step.includes('STV验证') ||
    step.includes('Integration') ||
    step.includes('整合') ||
    step === 'Start Query' ||
    step === '开始查询' ||
    step === 'Cleanup' ||
    step === '清理'
  ) {
    return (
      <Tag icon={<CloudOutlined />} color='blue'>
        Cloud Server
      </Tag>
    );
  }
  return null;
};

const QueryStepsModal: React.FC<QueryStepsModalProps> = ({
  visible,
  onClose,
  steps,
  loading = false,
  queryId,
}) => {
  return (
    <Modal
      title='Query Processing Steps'
      open={visible}
      onCancel={onClose}
      footer={null}
      width={700}
      style={{ top: 20 }}
      bodyStyle={{ maxHeight: 'calc(80vh - 100px)', overflowY: 'auto' }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '30px 0' }}>
          <Spin tip='Loading query steps...' />
        </div>
      ) : steps.length === 0 ? (
        <Empty description='No query steps data available' />
      ) : (
        <Timeline mode='left'>
          {queryId && (
            <div style={{ marginBottom: '16px' }}>
              <Text strong>Query ID: {queryId}</Text>
            </div>
          )}
          {steps.map((step, index) => (
            <Timeline.Item
              key={index}
              dot={getStatusIcon(step.details?.status)}
              color={
                step.details?.status === 'success'
                  ? 'green'
                  : step.details?.status === 'error'
                  ? 'red'
                  : step.details?.status === 'warning'
                  ? 'orange'
                  : 'blue'
              }
              label={formatTimestamp(step.timestamp)}
            >
              <div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '8px',
                  }}
                >
                  <Text strong>{step.step}</Text>
                  {getServerTypeTag(step.step, step.details)}
                </div>

                {step.details?.message && (
                  <Paragraph style={{ margin: '4px 0' }}>{step.details.message}</Paragraph>
                )}

                {/* Display query results count */}
                {step.details?.results_count !== undefined && (
                  <div>
                    <Badge
                      status='processing'
                      text={`Results count: ${step.details.results_count}`}
                    />
                  </div>
                )}

                {/* Display trajectories count */}
                {step.details?.trajectories_count !== undefined && (
                  <div>
                    <Badge
                      status='processing'
                      text={`Trajectories count: ${step.details.trajectories_count}`}
                    />
                  </div>
                )}

                {/* Display valid trajectories count */}
                {step.details?.valid_trajectories_count !== undefined && (
                  <div>
                    <Badge
                      status='success'
                      text={`Valid trajectories count: ${step.details.valid_trajectories_count}`}
                    />
                  </div>
                )}

                {/* Display fog server information */}
                {step.details?.fog_server && (
                  <div>
                    <Badge status='processing' text={`Fog server: ${step.details.fog_server}`} />
                    {step.details?.cassandra && (
                      <Text type='secondary'> ({step.details.cassandra})</Text>
                    )}
                  </div>
                )}

                {/* Display other details */}
                {Object.entries(step.details || {}).map(
                  ([key, value]) =>
                    ![
                      'status',
                      'message',
                      'results_count',
                      'trajectories_count',
                      'valid_trajectories_count',
                      'fog_server',
                      'cassandra',
                    ].includes(key) &&
                    typeof value !== 'object' && (
                      <div key={key}>
                        <Text type='secondary'>{key}: </Text>
                        <Text>{value}</Text>
                      </div>
                    )
                )}
              </div>
            </Timeline.Item>
          ))}
        </Timeline>
      )}
    </Modal>
  );
};

export default QueryStepsModal;
