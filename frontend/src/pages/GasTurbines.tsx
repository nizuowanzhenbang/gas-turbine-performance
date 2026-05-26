import { useEffect, useState } from 'react';
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../api/client';
import type { EquipmentStatus, GasTurbine } from '../api/types';
import { useAuthStore } from '../store/auth';

const STATUS_COLORS: Record<EquipmentStatus, string> = {
  RUNNING: 'green',
  STANDBY: 'default',
  MAINTENANCE: 'orange',
  OUTAGE: 'red',
  DECOMMISSIONED: 'gray',
};

const STATUS_LABELS: Record<EquipmentStatus, string> = {
  RUNNING: '运行',
  STANDBY: '备用',
  MAINTENANCE: '检修',
  OUTAGE: '停机',
  DECOMMISSIONED: '退役',
};

export default function GasTurbinesPage() {
  const canEdit = useAuthStore((s) => s.hasRole('ADMIN', 'PERFORMANCE_ENG'));
  const [rows, setRows] = useState<GasTurbine[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    api
      .get('/gas-turbines/')
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const onCreate = async () => {
    const values = await form.validateFields();
    await api.post('/gas-turbines/', values);
    message.success('燃机创建成功');
    setModalOpen(false);
    form.resetFields();
    load();
  };

  const columns = [
    { title: '编号', dataIndex: 'code', width: 90 },
    { title: '名称', dataIndex: 'name' },
    { title: '厂家', dataIndex: 'manufacturer', width: 110 },
    { title: '型号', dataIndex: 'model', width: 130 },
    { title: '铭牌出力', dataIndex: 'rated_power_mw', width: 110, render: (v: number) => `${v} MW` },
    {
      title: '设计效率',
      dataIndex: 'rated_efficiency',
      width: 110,
      render: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      title: '设计热耗率',
      dataIndex: 'rated_heat_rate_kj_kwh',
      width: 140,
      render: (v: number) => `${v.toFixed(0)} kJ/kWh`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (s: EquipmentStatus) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s]}</Tag>,
    },
    { title: '位置', dataIndex: 'location' },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <div style={{ fontSize: 16, fontWeight: 600 }}>燃机台账</div>
        {canEdit && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            新增燃机
          </Button>
        )}
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={rows}
        columns={columns}
        pagination={false}
        scroll={{ x: 1100 }}
      />

      <Modal
        title="新增燃机"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={onCreate}
        width={640}
      >
        <Form form={form} layout="vertical" initialValues={{ status: 'STANDBY' }}>
          <Form.Item
            label="编号（GT-NN）"
            name="code"
            rules={[{ required: true, pattern: /^GT-\d{2,3}$/, message: '格式：GT-01' }]}
          >
            <Input placeholder="GT-03" />
          </Form.Item>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="厂家" name="manufacturer">
            <Input placeholder="GE / Mitsubishi / Siemens" />
          </Form.Item>
          <Form.Item label="型号" name="model">
            <Input />
          </Form.Item>
          <Form.Item
            label="铭牌出力（MW）"
            name="rated_power_mw"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            label="设计热耗率（kJ/kWh）"
            name="rated_heat_rate_kj_kwh"
            rules={[{ required: true }]}
          >
            <InputNumber min={6000} max={15000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            label="设计效率（0-1）"
            name="rated_efficiency"
            rules={[{ required: true }]}
          >
            <InputNumber min={0.2} max={0.6} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select
              options={(Object.keys(STATUS_LABELS) as EquipmentStatus[]).map((s) => ({
                value: s,
                label: STATUS_LABELS[s],
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
