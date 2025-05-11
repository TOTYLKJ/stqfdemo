import React, { useEffect, useState, forwardRef, useImperativeHandle, useCallback } from 'react';
import { Table, Tag, Space, Button, Popconfirm } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { TablePaginationConfig } from 'antd/es/table';
import { FogServer } from '@/types/fogServer';
import { getFogServers } from '@/api/fogServer';

interface FogServerListProps {
  onEdit: (server: FogServer) => void;
  onDelete: (serverId: string) => void;
  onSelectionChange: (selectedRowKeys: string[]) => void;
}

export interface FogServerListRef {
  fetchServers: () => void;
}

const FogServerList = forwardRef<FogServerListRef, FogServerListProps>(
  ({ onEdit, onDelete, onSelectionChange }, ref) => {
    const [loading, setLoading] = useState(false);
    const [servers, setServers] = useState<FogServer[]>([]);
    const [pagination, setPagination] = useState({
      current: 1,
      pageSize: 10,
      total: 0,
    });

    const fetchServers = useCallback(
      async (page = pagination.current, pageSize = pagination.pageSize) => {
        setLoading(true);
        try {
          const data = await getFogServers({ page, page_size: pageSize });
          setServers(data.results);
          setPagination({
            current: page,
            pageSize,
            total: data.count,
          });
        } catch (error) {
          console.error('Failed to fetch server list:', error);
        } finally {
          setLoading(false);
        }
      },
      [pagination.current, pagination.pageSize]
    );

    useImperativeHandle(
      ref,
      () => ({
        fetchServers: () => fetchServers(pagination.current, pagination.pageSize),
      }),
      [fetchServers, pagination.current, pagination.pageSize]
    );

    useEffect(() => {
      fetchServers();
    }, [fetchServers]);

    const handleTableChange = (newPagination: TablePaginationConfig) => {
      fetchServers(newPagination.current as number, newPagination.pageSize as number);
    };

    const columns: ColumnsType<FogServer> = [
      {
        title: 'ID',
        dataIndex: 'id',
        key: 'id',
      },
      {
        title: 'Service Endpoint',
        dataIndex: 'service_endpoint',
        key: 'service_endpoint',
      },
      {
        title: 'Keyword Count',
        dataIndex: 'keywords',
        key: 'keywords',
        render: (keywords: string[]) => keywords.length,
      },
      {
        title: 'Load',
        dataIndex: 'keyword_load',
        key: 'keyword_load',
        render: (load: number) => `${load}%`,
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (status: string) => {
          const statusMap = {
            online: { color: 'success', text: 'Online' },
            offline: { color: 'default', text: 'Offline' },
            maintenance: { color: 'warning', text: 'Maintenance' },
          };
          const { color, text } = statusMap[status as keyof typeof statusMap];
          return <Tag color={color}>{text}</Tag>;
        },
      },
      {
        title: 'Creation Time',
        dataIndex: 'created_at',
        key: 'created_at',
        render: (time: string) => new Date(time).toLocaleString(),
      },
      {
        title: 'Actions',
        key: 'action',
        render: (_, record) => (
          <Space size='middle'>
            <Button type='text' icon={<EditOutlined />} onClick={() => onEdit(record)}>
              Edit
            </Button>
            <Popconfirm
              title='Are you sure you want to delete this server?'
              onConfirm={() => onDelete(record.id)}
            >
              <Button type='text' danger icon={<DeleteOutlined />}>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ];

    return (
      <Table
        rowKey='id'
        columns={columns}
        dataSource={servers}
        loading={loading}
        pagination={pagination}
        onChange={handleTableChange}
        rowSelection={{
          type: 'checkbox',
          onChange: (selectedRowKeys) => onSelectionChange(selectedRowKeys as string[]),
        }}
      />
    );
  }
);

FogServerList.displayName = 'FogServerList';

export default FogServerList;
