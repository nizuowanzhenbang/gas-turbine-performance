import { useEffect, useState } from 'react';
import { Card, Empty, Select, Space, Table, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import api from '../api/client';
import type { Degradation, GasTurbine, PerformanceCalculation } from '../api/types';

export default function DegradationPage() {
  const [turbines, setTurbines] = useState<GasTurbine[]>([]);
  const [selectedGt, setSelectedGt] = useState<number | null>(null);
  const [records, setRecords] = useState<Degradation[]>([]);
  const [trend, setTrend] = useState<PerformanceCalculation[]>([]);

  useEffect(() => {
    api.get('/gas-turbines/').then((r) => {
      setTurbines(r.data);
      if (r.data.length > 0) setSelectedGt(r.data[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedGt == null) return;
    api
      .get('/performance/degradation/', { params: { gas_turbine_id: selectedGt } })
      .then((r) => setRecords(r.data));
    api
      .get('/performance/', { params: { gas_turbine_id: selectedGt, days: 60, limit: 1000 } })
      .then((r) => setTrend([...r.data].reverse()));
  }, [selectedGt]);

  const chartOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['出力偏差 %', '热耗率偏差 %'] },
    grid: { left: 50, right: 30, top: 40, bottom: 40 },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', name: '%' },
    series: [
      {
        name: '出力偏差 %',
        type: 'line',
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.15 },
        data: trend.map((p) => [p.calc_time, p.power_deviation_pct]),
      },
      {
        name: '热耗率偏差 %',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: trend.map((p) => [p.calc_time, p.heat_rate_deviation_pct]),
      },
    ],
  };

  const columns = [
    { title: '记录号', dataIndex: 'record_no', width: 160 },
    { title: '周期起', dataIndex: 'period_start', width: 110 },
    { title: '周期止', dataIndex: 'period_end', width: 110 },
    {
      title: '平均出力偏差',
      dataIndex: 'avg_power_deviation_pct',
      width: 130,
      render: (v: number) => `${v.toFixed(2)}%`,
    },
    {
      title: '退化率',
      dataIndex: 'degradation_rate_pct_per_1000h',
      width: 130,
      render: (v: number) => `${v.toFixed(3)} %/1000h`,
    },
    {
      title: '运行小时',
      dataIndex: 'running_hours',
      width: 110,
      render: (v: number) => `${v.toFixed(1)} h`,
    },
    {
      title: '建议',
      width: 200,
      render: (_: unknown, r: Degradation) => (
        <Space>
          {r.wash_recommended && <Tag color="orange">建议水洗</Tag>}
          {r.overhaul_recommended && <Tag color="red">建议大修</Tag>}
          {!r.wash_recommended && !r.overhaul_recommended && <Tag color="green">正常</Tag>}
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title="性能退化趋势"
        extra={
          <Select
            value={selectedGt ?? undefined}
            onChange={setSelectedGt}
            style={{ minWidth: 160 }}
            options={turbines.map((t) => ({ value: t.id, label: `${t.code} ${t.name}` }))}
          />
        }
      >
        {trend.length === 0 ? (
          <Empty description="暂无趋势数据" />
        ) : (
          <ReactECharts option={chartOption} style={{ height: 320 }} />
        )}
      </Card>
      <Card title="月度退化记录">
        <Table
          rowKey="id"
          size="small"
          dataSource={records}
          columns={columns}
          pagination={false}
          locale={{ emptyText: '尚未生成 — 每日凌晨 2 点自动汇总' }}
        />
      </Card>
    </Space>
  );
}
