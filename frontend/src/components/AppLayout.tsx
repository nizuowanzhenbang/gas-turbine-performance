import { Avatar, Dropdown, Layout, Menu, Tag } from 'antd';
import {
  DashboardOutlined,
  ThunderboltOutlined,
  ClusterOutlined,
  LineChartOutlined,
  WarningOutlined,
  FallOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

const { Sider, Header, Content } = Layout;

const MENU = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '运行大屏' },
  { key: '/gas-turbines', icon: <ThunderboltOutlined />, label: '燃机台账' },
  { key: '/cc-units', icon: <ClusterOutlined />, label: '联合循环' },
  { key: '/performance', icon: <LineChartOutlined />, label: '性能分析' },
  { key: '/degradation', icon: <FallOutlined />, label: '退化趋势' },
  { key: '/alerts', icon: <WarningOutlined />, label: '告警中心' },
  { key: '/users', icon: <UserOutlined />, label: '用户管理', adminOnly: true },
];

const ROLE_LABELS: Record<string, string> = {
  ADMIN: '管理员',
  OPERATOR: '集控运行',
  PERFORMANCE_ENG: '性能工程师',
  MAINTENANCE: '检修工程师',
  VIEWER: '访客',
};

export default function AppLayout() {
  const nav = useNavigate();
  const loc = useLocation();
  const { fullName, role, logout } = useAuthStore();

  const items = MENU.filter((m) => !m.adminOnly || role === 'ADMIN').map(
    ({ key, icon, label }) => ({ key, icon, label }),
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider className="app-sider" width={220}>
        <div className="app-logo" style={{ height: 64, lineHeight: '64px' }}>
          ⚙ 燃机性能监测
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[loc.pathname]}
          items={items}
          onClick={({ key }) => nav(key)}
          style={{ background: 'transparent' }}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div style={{ color: '#6b7280' }}>
            智慧火电厂双线 · 燃气电厂线 · 性能监测子系统
          </div>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: '退出登录',
                  onClick: () => {
                    logout();
                    nav('/login');
                  },
                },
              ],
            }}
          >
            <div style={{ cursor: 'pointer' }}>
              <Avatar style={{ background: '#0e7490', marginRight: 8 }}>
                {fullName?.[0] ?? 'U'}
              </Avatar>
              <span style={{ marginRight: 8 }}>{fullName}</span>
              <Tag color="cyan">{role ? ROLE_LABELS[role] ?? role : ''}</Tag>
            </div>
          </Dropdown>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
