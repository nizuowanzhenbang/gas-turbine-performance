import { useEffect, useState } from 'react';
import { Button, Card, Input, Modal, Select, Space, Table, Tag, message } from 'antd';
import { CheckOutlined, CloseCircleOutlined } from '@ant-design/icons';
import api from '../api/client';
import type { Alert, AlertLevel, AlertStatus } from '../api/types';
import { useAuthStore } from '../store/auth';

const LEVEL_COLORS: Record<AlertLevel, string> = {
  INFO: 'blue',
  WARNING: 'orange',
  CRITICAL: 'red',
};

const STATUS_COLORS: Record<AlertStatus, string> = {
  OPEN: 'red',
  ACKNOWLEDGED: 'gold',
  RESOLVED: 'green',
  SUPPRESSED: 'default',
};

export default function AlertsPage() {
  const canHandle = useAuthStore((s) =>
    s.hasRole('ADMIN', 'OPERATOR', 'PERFORMANCE_ENG', 'MAINTENANCE'),
  );
  const [rows, setRows] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<AlertStatus | undefined>('OPEN');
  const [actionRow, setActionRow] = useState<{ row: Alert; type: 'ack' | 'resolve' } | null>(null);
  const [remarks, setRemarks] = useState('');

  const load = () => {
    setLoading(true);
    api
      .get('/alerts/', { params: statusFilter ? { status: statusFilter } : {} })
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(load, [statusFilter]);

  const doAction = async () => {
    if (!actionRow) return;
    const url = `/alerts/${actionRow.row.id}/${actionRow.type === 'ack' ? 'ack' : 'resolve'}`;
    await api.post(url, { remarks });
    message.success(actionRow.type === 'ack' ? '已确认' : '已闭环');
    setActionRow(null);
    setRemarks('');
    load();
  };

  const columns = [
    { title: '告警号', dataIndex: 'alert_no', width: 170 },
    {
      title: '级别',
      dataIndex: 'level',
      width: 90,
      render: (v: AlertLevel) => <Tag color={LEVEL_COLORS[v]}>{v}</Tag>,
    },
    { title: '类别', dataIndex: 'category', width: 110 },
    { title: '标题', dataIndex: 'title' },
    {
      title: '测量值',
      width: 140,
      render: (_: unknown, r: Alert) =>
        r.measured_value != null
          ? `${r.measured_value.toFixed(2)} ${r.unit} (阈值 ${r.threshold ?? '—'})`
          : '—',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (v: AlertStatus) => <Tag color={STATUS_COLORS[v]}>{v}</Tag>,
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      width: 160,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: '操作',
      width: 180,
      render: (_: unknown, r: Alert) =>
        canHandle && r.status === 'OPEN' ? (
          <Space>
            <Button
              size="small"
              icon={<CheckOutlined />}
              onClick={() => setActionRow({ row: r, type: 'ack' })}
            >
              确认
            </Button>
            <Button
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => setActionRow({ row: r, type: 'resolve' })}
            >
              闭环
            </Button>
          </Space>
        ) : canHandle && r.status === 'ACKNOWLEDGED' ? (
          <Button
            size="small"
            danger
            icon={<CloseCircleOutlined />}
            onClick={() => setActionRow({ row: r, type: 'resolve' })}
          >
            闭环
          </Button>
        ) : null,
    },
  ];

  return (
    <Card
      title="告警中心"
      extra={
        <Select
          allowClear
          placeholder="全部状态"
          value={statusFilter}
          onChange={setStatusFilter}
          style={{ minWidth: 160 }}
          options={[
            { value: 'OPEN', label: '未关闭' },
            { value: 'ACKNOWLEDGED', label: '已确认' },
            { value: 'RESOLVED', label: '已闭环' },
            { value: 'SUPPRESSED', label: '已抑制' },
          ]}
        />
      }
    >
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        columns={columns}
        pagination={{ pageSize: 20 }}
        scroll={{ x: 1200 }}
      />

      <Modal
        title={actionRow?.type === 'ack' ? '确认告警' : '闭环告警'}
        open={actionRow != null}
        onCancel={() => {
          setActionRow(null);
          setRemarks('');
        }}
        onOk={doAction}
      >
        <p>{actionRow?.row.title}</p>
        <Input.TextArea
          rows={3}
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          placeholder="处理备注（可选）"
        />
      </Modal>
    </Card>
  );
}
