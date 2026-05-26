import { useEffect, useState } from 'react';
import { Table, Tag } from 'antd';
import api from '../api/client';
import type { CCUnit, EquipmentStatus } from '../api/types';

const STATUS_COLORS: Record<EquipmentStatus, string> = {
  RUNNING: 'green',
  STANDBY: 'default',
  MAINTENANCE: 'orange',
  OUTAGE: 'red',
  DECOMMISSIONED: 'gray',
};

export default function CCUnitsPage() {
  const [rows, setRows] = useState<CCUnit[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .get('/cc-units/')
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    { title: '编号', dataIndex: 'code', width: 90 },
    { title: '名称', dataIndex: 'name' },
    { title: '配置', dataIndex: 'configuration', width: 90 },
    {
      title: '联合循环总出力',
      dataIndex: 'rated_total_power_mw',
      width: 150,
      render: (v: number) => `${v} MW`,
    },
    {
      title: '联合循环效率',
      dataIndex: 'rated_cc_efficiency',
      width: 130,
      render: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (s: EquipmentStatus) => <Tag color={STATUS_COLORS[s]}>{s}</Tag>,
    },
  ];

  return (
    <div>
      <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>联合循环机组</div>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={rows}
        columns={columns}
        pagination={false}
      />
    </div>
  );
}
