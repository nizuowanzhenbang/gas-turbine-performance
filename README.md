# 燃机性能监测平台 · Gas Turbine Performance

> 燃机交了几千万的电费表，效率掉了 1% 你能立刻看出来吗？
> 一台 300 MW 9F 燃机，效率掉 1% 一年多烧的天然气够再买一台保时捷。
> 这个系统盯着这个数 —— 把 DCS 里的运行参数按 ISO 大气工况一秒修正，和出厂基线一比，**0.5% 的悄悄下滑当场显形**。

> ⚠️ **边界声明**：本仓库是「智慧火电厂双线总览」燃气电厂线的子系统，专注**性能 + 健康监测**；不替代 DCS 控制、TSI 保护、CEMS 排放。所有阈值与修正系数为工程示例，正式投运前需由性能工程师按本厂 PG 试验结果重写。

## 🎯 30 秒看明白：你是谁，它帮你做什么

| 你是谁                      | 它帮你做什么                                                                 |
| --------------------------- | ---------------------------------------------------------------------------- |
| 集控运行员                  | 大屏一眼看到每台燃机的修正后出力、未关闭告警；振动 / EGT 散布异常立刻弹窗   |
| 性能工程师                  | 手动点"立即计算"跑 ISO 修正性能、看月度退化率曲线、按机组管理出厂基线        |
| 检修工程师                  | 收性能退化触发的检修建议（水洗 / 大修），CRITICAL 告警自动落地到检修工单系统 |
| 燃料管理（兄弟系统）        | 自动收到本系统回传的"修正后效率 + 热耗率"，用于燃料费用对账                  |
| 厂长 / 安环部领导           | 看 24h 发电量、机组运行率、未关闭 CRITICAL 数量，不用查 DCS                  |

## 🧩 核心场景

### ⚙ ISO 大气工况修正

燃机出力天生跟环境跑——夏天热、冬天冷、上山下山气压变，**不修正就没法和厂家保证值、和昨天的自己比**。

系统每分钟为每台 RUNNING 燃机取最近 15 分钟运行数据（环境温度/压力/湿度/燃料流量/LHV/出力/排温），按以下三个系数把实测拉回到 ISO 15°C、101.325 kPa、60% 湿度：

```
修正后出力 = 实测出力 / (k_T · k_P · k_H)
```

> 系数采用工程常用多项式（如温度 -0.5%/°C），可由性能工程师在基线页替换为厂家修正曲线。参考 **ISO 2314 / ASME PTC 22 / DL/T 1066**。

### 📉 性能退化跟踪

每条 ISO 修正后的批次记录都会和最贴近的负荷基线比对，得到「出力偏差 %」和「热耗率偏差 %」。每日凌晨 2 点自动汇总过去 7 天，落入 `degradation_records` 表，并按规则推荐：

- 出力降 ≥ 3% **或** 距上次水洗 ≥ 2000h → 在线/离线水洗
- 出力降 ≥ 8% **或** 累计 ≥ 24000h → 大修

退化记录 + 退化趋势图都按机组分开看，**水洗后还会出现负退化率**（性能回升）。

### 🩺 健康监测（振动 / EGT / 轴位移）

每 5 分钟扫一次最新读数：

| 量纲           | 判据                                          | 触发                          |
| -------------- | --------------------------------------------- | ----------------------------- |
| 振动 mm/s      | ISO 10816 区域 A→B→C→D                        | C 区 WARNING / D 区 CRITICAL  |
| EGT 6 点散布   | max-min ≥ 50°C，并定位偏离均值最远的热电偶    | WARNING；≥ 80°C 升 CRITICAL   |
| 推力轴承位移   | \|axial\| ≥ 0.8 mm / 1.2 mm                   | WARNING / CRITICAL            |

### 🔗 跨系统联动（已存根 4 条 OUT / 1 条 IN）

| 方向 | 对端                       | 触发条件                                                 |
| ---- | -------------------------- | -------------------------------------------------------- |
| OUT  | equipment-inspection       | CRITICAL 性能退化 → 提缺陷工单                           |
| OUT  | plant-safety               | CRITICAL 振动 → 提安全事件                               |
| OUT  | gas-fuel-metering          | 每次性能计算回传效率/热耗，供对账"度电耗气量"            |
| IN   | gas-fuel-metering          | 接收最新 LHV → 内存缓存，下次性能计算可优先采用          |

> 所有出库走 httpx + 3s 超时 + 2 次指数退避 + `X-Integration-Secret` 头；失败不抛，仅在 `alert.push_remarks` 留痕。

### 🛡 告警去重 + 闭环

同对象 + 同 category 已有 OPEN 告警时，**只刷新 measured_value 和 triggered_at**，不再连环发。运行员可以确认（ACK）→ 检修员闭环（RESOLVED），全程留人留时间。

## 🗂 仓库一览

```
gas-turbine-performance/
├── backend/          FastAPI + SQLAlchemy 2.x + APScheduler + JWT/RBAC
│   ├── app/
│   │   ├── models/   5 张 ORM（user / equipment / reading / performance / alert）
│   │   ├── routers/  13 个 router（auth/users/gas-turbines/hrsg/steam-turbines/
│   │   │             cc-units/readings/performance/baselines/alerts/dashboard/
│   │   │             integration/upload）
│   │   ├── services/ 算法 + 调度 + 告警 + 跨系统出库
│   │   └── seed_data.py  幂等演示数据：2 台燃机 + 24h 读数 + 3 条告警
│   └── tests/        7 个 pytest 文件 / 107 测试全过，sqlite + TestClient
├── frontend/         Vite + React 18 + TS + Ant Design 5 + ECharts + Zustand
│   └── src/          7 个页面（登录/大屏/燃机/CC/性能/退化/告警/用户）
└── docker-compose.yml  postgres + backend(8011) + frontend(5181)
```

## 🔧 技术栈与设计取舍

- **后端**：FastAPI 0.115 / SQLAlchemy 2.0 / Pydantic 2.9 / APScheduler 3.10 / httpx 0.27
- **前端**：Vite 5 / React 18 / TypeScript 5.6 / Ant Design 5.21 / ECharts 5.5 / Zustand 5
- **数据库**：PostgreSQL 16；测试时用 SQLite 内存
- **密码**：bcrypt + SHA-256 预摘要（绕开 72 字节上限），不依赖已停更的 passlib
- **业务编号**：`PERF-YYYYMMDD-NNNN` / `DEG-YYYYMM-NN` / `AL-YYYYMMDD-NNNN`
- **端口**：backend **8011**、frontend **5181**（与同线 [gas-fuel-metering](https://github.com/nizuowanzhenbang/gas-fuel-metering) 8010/5180 错开）

## 🚀 起步

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[test]
cp .env.example .env
python -m app.seed_data           # 注入演示数据
uvicorn app.main:app --port 8011 --reload

# 前端
cd ../frontend
npm install
npm run dev                       # http://localhost:5181

# 或一键 docker
docker compose up -d --build
```

演示账号（密码统一 `demo123`）：

| 用户名      | 角色             | 能干什么                                   |
| ----------- | ---------------- | ------------------------------------------ |
| admin       | ADMIN            | 全权限 + 用户管理                          |
| operator    | OPERATOR         | 录读数、跑性能计算、处理告警               |
| perfeng     | PERFORMANCE_ENG  | 管燃机/基线、跑性能计算                    |
| maintenance | MAINTENANCE      | 处理告警、看检修建议                       |
| viewer      | VIEWER           | 只读                                       |

## 🧪 测试

```bash
cd backend && pytest -v
```

**107 测试全过**（7 个文件）：48 算法单测（ISO 修正 / 热耗率 / EGT 散布 / 退化率 / ISO 10816 振动等级）+ 11 调度作业测试（perf_calc / health_check / degradation_daily + 告警去重）+ 48 路由集成测试（auth+RBAC、燃机/HRSG/ST CRUD、读数+性能批次、告警生命周期、跨系统接收、CSV 上传）。SQLite 内存 DB + FastAPI TestClient，全程不依赖 PostgreSQL。

## 🔗 它在大图中的位置

属于 **[smart-power-plant](https://github.com/nizuowanzhenbang/smart-power-plant)** 总览 → **燃气电厂线** 第 2 个子系统：

| 上游                                                           | 本系统               | 下游                                                                                     |
| -------------------------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------- |
| DCS 实时点 / [gas-fuel-metering](https://github.com/nizuowanzhenbang/gas-fuel-metering)（LHV） | 性能 + 健康监测      | [equipment-inspection](https://github.com/nizuowanzhenbang/equipment-inspection)（缺陷工单） / [plant-safety](https://github.com/nizuowanzhenbang/plant-safety)（安全事件） |

## 📜 License

仅供智慧火电厂内部研究与教学使用。


## 持续维护

[开发与验收说明](docs/MAINTENANCE.md)：自动检查、回归测试与演示边界。
