import { useEffect, useState } from 'react';
import { Button, Card, InputNumber, Select, Space, Table, Tag, message } from 'antd';
import { CalculatorOutlined } from '@ant-design/icons';
import api from '../api/client';
import type { GasTurbine, PerformanceCalculation } from '../api/types';
import { useAuthStore } from '../store/auth';

export default function PerformancePage() {
  const canCalc = useAuthStore((s) => s.hasRole('ADMIN', 'PERFORMANCE_ENG', 'OPERATOR'));
  const [turbines, setTurbines] = useState<GasTurbine[]>([]);
  const [selectedGt, setSelectedGt] = useState<number | null>(null);
  const [window, setWindow] = useState(15);
  const [rows, setRows] = useState<PerformanceCalculation[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    api.get('/gas-turbines/').then((r) => {
      setTurbines(r.data);
      if (r.data.length > 0) setSelectedGt(r.data[0].id);
    });
  }, []);

  const load = () => {
    if (selectedGt == null) return;
    setLoading(true);
    api
      .get('/performance/', { params: { gas_turbine_id: selectedGt, days: 14, limit: 200 } })
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, [selectedGt]);

  const trigger = async () => {
    if (selectedGt == null) return;
    setTriggering(true);
    try {
      await api.post('/performance/calculate', {
        gas_turbine_id: selectedGt,
        window_minutes: window,
      });
      message.success('性能计算完成');
      load();
    } finally {
      setTriggering(false);
    }
  };

  const columns = [
    { title: '批次号', dataIndex: 'batch_no', width: 180 },
    {
      title: '计算时刻',
      dataIndex: 'calc_time',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: '修正后出力',
      dataIndex: 'corrected_power_mw',
      width: 130,
      render: (v: number) => `${v.toFixed(2)} MW`,
    },
    {
      title: '修正后效率',
      dataIndex: 'corrected_efficiency',
      width: 120,
      render: (v: number) => `${(v * 100).toFixed(2)}%`,
    },
    {
      title: '修正后热耗率',
      dataIndex: 'corrected_heat_rate_kj_kwh',
      width: 150,
      render: (v: number) => `${v.toFixed(0)} kJ/kWh`,
    },
    {
      title: '出力偏差',
      dataIndex: 'power_deviation_pct',
      width: 110,
      render: (v: number) => {
        const color = v >= 5 ? 'red' : v >= 3 ? 'orange' : 'green';
        return <Tag color={color}>{v.toFixed(2)}%</Tag>;
      },
    },
    {
      title: 'EGT 散布',
      dataIndex: 'egt_spread_c',
      width: 110,
      render: (v: number) => `${v.toFixed(1)} °C`,
    },
    {
      title: 'CC 总出力',
      dataIndex: 'cc_total_power_mw',
      width: 120,
      render: (v: number | null) => (v != null ? `${v.toFixed(1)} MW` : '—'),
    },
  ];

  return (
    <Card
      title="性能计算批次（ISO 大气工况修正）"
      extra={
        <Space>
          <Select
            value={selectedGt ?? undefined}
            onChange={setSelectedGt}
            style={{ minWidth: 160 }}
            options={turbines.map((t) => ({ value: t.id, label: `${t.code} ${t.name}` }))}
          />
          <InputNumber
            min={5}
            max={240}
            value={window}
            onChange={(v) => setWindow(v ?? 15)}
            addonAfter="分钟"
          />
          {canCalc && (
            <Button
              type="primary"
              icon={<CalculatorOutlined />}
              loading={triggering}
              onClick={trigger}
            >
              立即计算
            </Button>
          )}
        </Space>
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
    </Card>
  );
}
