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

// Herramientas externas (sobrescribibles con VITE_GRAFANA_URL, etc.)
export const EXTERNAL = {
  grafana: import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3001',
  prometheus: import.meta.env.VITE_PROM_URL || 'http://localhost:9090',
  alertmanager: import.meta.env.VITE_ALERTMANAGER_URL || 'http://localhost:9093',
};

export function grafanaExploreLoki(host: string) {
  const q = encodeURIComponent(JSON.stringify({
    datasource: 'Loki',
    queries: [{ expr: `{host="${host}"}`, refId: 'A' }],
    range: { from: 'now-6h', to: 'now' },
  }));
  return `${EXTERNAL.grafana}/explore?orgId=1&left=${q}`;
}

export default api;
