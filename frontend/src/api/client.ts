import axios from 'axios';
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' });
api.interceptors.request.use(c => {
  const t = localStorage.getItem('token');
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});
api.interceptors.response.use(r => r, e => {
  if (e.response?.status === 401 && !location.pathname.includes('/login')) {
    localStorage.removeItem('token');
    location.hash = '#/login';
  }
  return Promise.reject(e);
});
export default api;
