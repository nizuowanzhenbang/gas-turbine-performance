import { useEffect, useState } from 'react';
import { Card, Col, Empty, Row, Select, Spin, Statistic, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import api from '../api/client';
import type { DashboardSummary, GasTurbine, PerfTrendPoint } from '../api/types';

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [turbines, setTurbines] = useState<GasTurbine[]>([]);
  const [selectedGt, setSelectedGt] = useState<number | null>(null);
  const [trend, setTrend] = useState<PerfTrendPoint[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get('/dashboard/summary').then((r) => setSummary(r.data));
    api.get('/gas-turbines/').then((r) => {
      setTurbines(r.data);
      if (r.data.length > 0) setSelectedGt(r.data[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedGt == null) return;
    setLoading(true);
    api
      .get(`/dashboard/performance-trend`, { params: { gas_turbine_id: selectedGt, days: 14 } })
      .then((r) => setTrend(r.data.series ?? []))
      .finally(() => setLoading(false));
  }, [selectedGt]);

  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['修正后出力 MW', '出力偏差 %', '热耗率 kJ/kWh'] },
    grid: { left: 50, right: 50, top: 40, bottom: 40 },
    xAxis: { type: 'time' },
    yAxis: [
      { type: 'value', name: 'MW / %', position: 'left' },
      { type: 'value', name: 'kJ/kWh', position: 'right' },
    ],
    series: [
      {
        name: '修正后出力 MW',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: trend.map((p) => [p.t, p.corrected_power_mw]),
      },
      {
        name: '出力偏差 %',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: trend.map((p) => [p.t, p.power_deviation_pct]),
      },
      {
        name: '热耗率 kJ/kWh',
        type: 'line',
        smooth: true,
        showSymbol: false,
        yAxisIndex: 1,
        data: trend.map((p) => [p.t, p.corrected_heat_rate_kj_kwh]),
      },
    ],
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card className="metric-card">
            <Statistic
              title="燃机运行 / 总数"
              value={`${summary?.gas_turbines.running ?? 0} / ${summary?.gas_turbines.total ?? 0}`}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="metric-card">
            <Statistic title="联合循环机组" value={summary?.combined_cycle_units ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="metric-card">
            <Statistic
              title="24h 发电量"
              value={summary?.generation_24h_mwh ?? 0}
              suffix="MWh"
              precision={1}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="metric-card">
            <Statistic
              title="未关闭告警"
              value={summary?.alerts.open ?? 0}
              suffix={
                summary && summary.alerts.critical > 0 ? (
                  <Tag color="red">CRITICAL × {summary.alerts.critical}</Tag>
                ) : null
              }
              valueStyle={{
                color: (summary?.alerts.critical ?? 0) > 0 ? '#dc2626' : undefined,
              }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        style={{ marginTop: 16 }}
        title="性能趋势（近 14 天）"
        extra={
          <Select
            value={selectedGt ?? undefined}
            onChange={setSelectedGt}
            style={{ minWidth: 160 }}
            options={turbines.map((t) => ({ value: t.id, label: `${t.code} ${t.name}` }))}
          />
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin />
          </div>
        ) : trend.length === 0 ? (
          <Empty description="暂无数据 — 请运行 python -m app.seed_data 注入演示数据" />
        ) : (
          <ReactECharts option={trendOption} style={{ height: 360 }} />
        )}
      </Card>
    </div>
  );
}
