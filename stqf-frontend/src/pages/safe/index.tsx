import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  Divider,
  Table,
  message,
  Typography,
  Row,
  Col,
  InputNumber,
  Alert,
  Tooltip,
  Radio,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  MinusCircleOutlined,
  SearchOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { processQuery, QueryItem, QueryRequest } from '@api/query';
import QueryStepsModal from '@/components/QueryStepsModal';
import { QueryStep } from '@/components/QueryStepsModal';

const { Title } = Typography;

interface QueryResult {
  decrypted_traj_id: string;
  decrypted_date: string;
  rid: string;
}

const SafeQueryPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<QueryResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [querySteps, setQuerySteps] = useState<QueryStep[]>([]);
  const [stepsModalVisible, setStepsModalVisible] = useState(false);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<string>('auto'); // Default to auto algorithm

  // Table column definitions
  const columns = [
    {
      title: 'Trajectory ID',
      dataIndex: 'decrypted_traj_id',
      key: 'decrypted_traj_id',
    },
    {
      title: 'Date',
      dataIndex: 'decrypted_date',
      key: 'decrypted_date',
    },
    {
      title: 'Query ID',
      dataIndex: 'rid',
      key: 'rid',
    },
  ];

  // Handle query submission
  const handleSubmit = async (values: any) => {
    try {
      setLoading(true);
      setError(null);
      setQuerySteps([]);

      // Build query request
      const queryRequest: QueryRequest = {
        queries: values.queries.map((q: any) => {
          const query: QueryItem = {
            keyword: parseInt(q.keyword),
          };

          // Add Morton range (if provided)
          if (q.morton_min || q.morton_max) {
            query.morton_range = {
              min: q.morton_min || '',
              max: q.morton_max || '',
            };
          }

          // Add grid range (if provided)
          if (q.grid_min_x || q.grid_min_y || q.grid_max_x || q.grid_max_y) {
            query.grid_range = {
              min_x: q.grid_min_x || 0,
              min_y: q.grid_min_y || 0,
              min_z: q.grid_min_z || 0,
              max_x: q.grid_max_x || 0,
              max_y: q.grid_max_y || 0,
              max_z: q.grid_max_z || 0,
            };
          }

          // Add point range (if provided)
          if (q.lat_min || q.lon_min || q.time_min || q.lat_max || q.lon_max || q.time_max) {
            query.point_range = {
              lat_min: q.lat_min || 0,
              lon_min: q.lon_min || 0,
              time_min: q.time_min || 0,
              lat_max: q.lat_max || 0,
              lon_max: q.lon_max || 0,
              time_max: q.time_max || 0,
            };
          }

          return query;
        }),
        time_span: parseInt(values.time_span) || 10000,
        algorithm: values.algorithm === 'auto' ? 'sstp' : values.algorithm,
      };

      console.log('Query request:', queryRequest);

      // Send query request
      const response = await processQuery(queryRequest);

      if (response.status === 'success') {
        // Flatten 2D array to 1D array
        const flatResults = response.data.valid_trajectories.flat();
        setResults(flatResults);
        message.success(`Query successful, found ${response.data.total_count} results`);

        // Save query step information
        if (response.data.steps && response.data.steps.length > 0) {
          setQuerySteps(response.data.steps);
          // Automatically display steps modal
          setStepsModalVisible(true);
        }
      } else {
        setError('Query failed');
        message.error('Query failed');

        // Even if query fails, try to display step information
        if (response.steps && response.steps.length > 0) {
          setQuerySteps(response.steps);
          setStepsModalVisible(true);
        }
      }
    } catch (error) {
      console.error('Query error:', error);
      setError('Query error: ' + (error.message || 'Unknown error'));
      message.error('Query error: ' + (error.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[0, 24]}>
        <Col span={24}>
          <Card>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 16,
              }}
            >
              <Title level={4}>Query Results</Title>
              <div>
                {results && results.length > 0 && (
                  <Badge
                    color='blue'
                    text={`Algorithm: ${
                      selectedAlgorithm === 'auto'
                        ? 'Auto (SSTP)'
                        : selectedAlgorithm === 'sstp'
                        ? 'SSTP Algorithm'
                        : 'Traversal Algorithm'
                    }`}
                    style={{ marginRight: 16 }}
                  />
                )}
                {querySteps.length > 0 && (
                  <Tooltip title='View query processing steps'>
                    <Button
                      type='primary'
                      icon={<InfoCircleOutlined />}
                      onClick={() => setStepsModalVisible(true)}
                    >
                      View Processing Steps
                    </Button>
                  </Tooltip>
                )}
              </div>
            </div>
            {error && <Alert message={error} type='error' showIcon style={{ marginBottom: 16 }} />}
            <Table
              columns={columns}
              dataSource={results}
              rowKey={(record, index) =>
                record.decrypted_traj_id && record.rid
                  ? `${record.decrypted_traj_id}_${record.rid}`
                  : `row_${index}`
              }
              pagination={{ pageSize: 10 }}
              loading={loading}
            />
          </Card>
        </Col>

        <Col span={24}>
          <Card>
            <Title level={4}>Safe Query</Title>
            <Form
              form={form}
              name='safe_query_form'
              onFinish={handleSubmit}
              autoComplete='off'
              layout='vertical'
              initialValues={{
                time_span: 10000,
                algorithm: 'auto', // Default to Auto (which uses SSTP)
                queries: [{}], // Default add one empty query condition
              }}
              onValuesChange={(changedValues) => {
                // Update state when algorithm selection changes
                if (changedValues.algorithm) {
                  setSelectedAlgorithm(changedValues.algorithm);
                }
              }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name='time_span'
                    label='Time Span'
                    rules={[{ required: true, message: 'Please enter time span' }]}
                  >
                    <InputNumber style={{ width: '100%' }} min={1} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name='algorithm'
                    label='Query Algorithm'
                    tooltip='Select query algorithm: Auto (uses SSTP), SSTP for precise queries, or Traversal for wide-range queries'
                  >
                    <Radio.Group>
                      <Radio.Button value='auto'>Auto</Radio.Button>
                      <Radio.Button value='sstp'>SSTP Algorithm</Radio.Button>
                      <Radio.Button value='traversal'>Traversal Algorithm</Radio.Button>
                    </Radio.Group>
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation='left'>Query Conditions</Divider>

              <Form.List name='queries'>
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }) => (
                      <div key={key} style={{ marginBottom: 24 }}>
                        <Card
                          size='small'
                          title={`Condition ${name + 1}`}
                          extra={
                            fields.length > 1 ? (
                              <Button
                                danger
                                icon={<MinusCircleOutlined />}
                                onClick={() => remove(name)}
                              >
                                Remove
                              </Button>
                            ) : null
                          }
                        >
                          <Row gutter={[16, 16]}>
                            <Col span={24}>
                              <Form.Item
                                {...restField}
                                name={[name, 'keyword']}
                                label='Keyword'
                                rules={[{ required: true, message: 'Please enter keyword' }]}
                              >
                                <Input placeholder='Enter keyword' />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Divider orientation='left'>Morton Range</Divider>
                          <Row gutter={[16, 16]}>
                            <Col span={12}>
                              <Form.Item {...restField} name={[name, 'morton_min']} label='Min'>
                                <Input placeholder='Min morton value' />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item {...restField} name={[name, 'morton_max']} label='Max'>
                                <Input placeholder='Max morton value' />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Divider orientation='left'>Grid Range</Divider>
                          <Row gutter={[16, 16]}>
                            <Col span={8}>
                              <Form.Item {...restField} name={[name, 'grid_min_x']} label='Min X'>
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item {...restField} name={[name, 'grid_min_y']} label='Min Y'>
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item {...restField} name={[name, 'grid_min_z']} label='Min Z'>
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item {...restField} name={[name, 'grid_max_x']} label='Max X'>
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item {...restField} name={[name, 'grid_max_y']} label='Max Y'>
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item {...restField} name={[name, 'grid_max_z']} label='Max Z'>
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Divider orientation='left'>Point Range</Divider>
                          <Row gutter={[16, 16]}>
                            <Col span={8}>
                              <Form.Item
                                {...restField}
                                name={[name, 'lat_min']}
                                label='Min Latitude'
                              >
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item
                                {...restField}
                                name={[name, 'lon_min']}
                                label='Min Longitude'
                              >
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item {...restField} name={[name, 'time_min']} label='Min Time'>
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item
                                {...restField}
                                name={[name, 'lat_max']}
                                label='Max Latitude'
                              >
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item
                                {...restField}
                                name={[name, 'lon_max']}
                                label='Max Longitude'
                              >
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={8}>
                              <Form.Item {...restField} name={[name, 'time_max']} label='Max Time'>
                                <InputNumber style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>
                        </Card>
                      </div>
                    ))}

                    <Form.Item>
                      <Button
                        type='dashed'
                        onClick={() => add()}
                        icon={<PlusOutlined />}
                        style={{ width: '100%' }}
                      >
                        Add Query Condition
                      </Button>
                    </Form.Item>
                  </>
                )}
              </Form.List>

              <Form.Item>
                <Button
                  type='primary'
                  htmlType='submit'
                  loading={loading}
                  icon={<SearchOutlined />}
                >
                  Execute Query
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>

      <QueryStepsModal
        visible={stepsModalVisible}
        steps={querySteps}
        onClose={() => setStepsModalVisible(false)}
        queryId={results.length > 0 && results[0].rid ? results[0].rid : ''}
      />
    </div>
  );
};

export default SafeQueryPage;
