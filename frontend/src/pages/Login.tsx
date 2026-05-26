import { Alert, Button, Card, Form, Input, Typography } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { useAuthStore } from '../store/auth';

const { Title, Paragraph } = Typography;

interface LoginValues {
  username: string;
  password: string;
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setSession = useAuthStore((s) => s.setSession);
  const nav = useNavigate();

  const onFinish = async (values: LoginValues) => {
    setError(null);
    setLoading(true);
    try {
      const resp = await api.post('/auth/login', values);
      setSession({
        token: resp.data.access_token,
        username: values.username,
        fullName: resp.data.full_name,
        role: resp.data.role,
      });
      nav('/dashboard', { replace: true });
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #082f49 0%, #0e7490 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <Card style={{ width: 420 }} bordered={false}>
        <Title level={3} style={{ marginBottom: 4 }}>
          ⚙ 燃机性能监测平台
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 24 }}>
          Gas Turbine &amp; Combined Cycle Performance Monitor
        </Paragraph>
        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" block htmlType="submit" loading={loading}>
            登录
          </Button>
        </Form>
        <Paragraph type="secondary" style={{ marginTop: 16, fontSize: 12 }}>
          演示账号：admin / operator / perfeng / maintenance / viewer · 统一密码 demo123
        </Paragraph>
      </Card>
    </div>
  );
}
