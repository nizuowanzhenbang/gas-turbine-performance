import axios from 'axios';
import { message } from 'antd';
import { useAuthStore } from '../store/auth';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      useAuthStore.getState().logout();
      if (location.pathname !== '/login') {
        location.href = '/login';
      }
    } else if (status === 403) {
      message.error('当前角色无权操作');
    } else {
      const detail = error?.response?.data?.detail;
      message.error(typeof detail === 'string' ? detail : '请求失败');
    }
    return Promise.reject(error);
  },
);

export default api;
