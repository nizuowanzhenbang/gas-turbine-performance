import { useEffect, useState } from 'react';
import { Button, Form, Input, Modal, Select, Space, Switch, Table, Tag, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../api/client';
import type { UserInfo, UserRole } from '../api/types';

const ROLE_LABELS: Record<UserRole, string> = {
  ADMIN: '管理员',
  OPERATOR: '集控运行',
  PERFORMANCE_ENG: '性能工程师',
  MAINTENANCE: '检修工程师',
  VIEWER: '访客',
};

export default function UsersPage() {
  const [rows, setRows] = useState<UserInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    api
      .get('/users/')
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const onCreate = async () => {
    const values = await form.validateFields();
    await api.post('/users/', values);
    message.success('用户创建成功');
    setModalOpen(false);
    form.resetFields();
    load();
  };

  const columns = [
    { title: '用户名', dataIndex: 'username', width: 140 },
    { title: '姓名', dataIndex: 'full_name' },
    {
      title: '角色',
      dataIndex: 'role',
      width: 140,
      render: (v: UserRole) => <Tag color="cyan">{ROLE_LABELS[v]}</Tag>,
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 80,
      render: (v: boolean) => (v ? <Tag color="green">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: '最近登录',
      dataIndex: 'last_login_at',
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : '—'),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <div style={{ fontSize: 16, fontWeight: 600 }}>用户管理</div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新增用户
        </Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={rows}
        columns={columns}
        pagination={false}
      />
      <Modal
        title="新增用户"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={onCreate}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ role: 'VIEWER', is_active: true }}
        >
          <Form.Item label="用户名" name="username" rules={[{ required: true, min: 3 }]}>
            <Input />
          </Form.Item>
          <Form.Item label="姓名" name="full_name">
            <Input />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, min: 6, message: '至少 6 位' }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item label="角色" name="role">
            <Select
              options={(Object.keys(ROLE_LABELS) as UserRole[]).map((r) => ({
                value: r,
                label: ROLE_LABELS[r],
              }))}
            />
          </Form.Item>
          <Form.Item label="启用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
