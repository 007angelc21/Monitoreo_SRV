import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../api/client';

function sevBadge(s: string) {
  const k = s === 'CRITICAL' ? 'crit' : s === 'WARNING' ? 'warn' : 'info';
  return <span className={`badge ${k}`}>{s}</span>;
}

function healthBadge(v: string) {
  const ok = v === 'ok' || v === 'running';
  return <span className={`badge ${ok ? 'ok' : 'crit'}`}>{v}</span>;
}

export function Maintenance() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState('');
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: async () => (await api.get('/api/health')).data, refetchInterval: 30000 });
  const { data: servers } = useQuery({ queryKey: ['servers'], queryFn: async () => (await api.get('/api/servers?limit=200')).data });
  const { data: alerts } = useQuery({ queryKey: ['alerts-firing'], queryFn: async () => (await api.get('/api/alerts?status=firing&limit=100')).data, refetchInterval: 15000 });

  async function act(id: string, op: 'ack' | 'resolve') {
    setMsg('');
    try {
      await api.post(`/api/alerts/${id}/${op}`);
      qc.invalidateQueries({ queryKey: ['alerts-firing'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
    } catch (e: any) {
      setMsg(e?.response?.data?.error?.message ?? 'Operación no permitida (requiere rol operador o administrador).');
    }
  }

  const items: any[] = servers?.items ?? [];
  const al: any[] = alerts?.items ?? [];
  return (
    <div>
      <h1>Mantenimiento</h1>
      <h2>Formularios y accesos</h2>
      <div className="toolbar">
        <Link className="btn" to="/servers">Agregar servidor</Link>
        <Link className="btn" to="/vmware">Ver infraestructura VMware</Link>
      </div>
      <p className="meta">Alta de vCenters y reglas de alerta se gestionan vía API (`/api/docs`). Descubrimiento: `POST /api/vcenters/{'{id}'}/discover`.</p>
      <h2>Estado de salud</h2>
      {!health ? <p className="empty">Consultando...</p> : (
        <div className="cards">
          {Object.entries(health).map(([k, v]) => (
            <div className="card" key={k}>
              <div className="t">{k}</div>
              <div style={{ marginTop: 6 }}>{healthBadge(String(v).slice(0, 40))}</div>
            </div>))}
        </div>)}
      <h2>Servidores ({servers?.total ?? items.length})</h2>
      {items.length === 0 ? <p className="empty">Sin servidores registrados.</p> : (
        <div className="panel">
          <table className="grid">
            <thead><tr><th>Servidor</th><th>IP</th><th>SO</th><th>Agente</th></tr></thead>
            <tbody>
              {items.map((s: any) => (
                <tr key={s.id}>
                  <td><Link to={`/servers/${s.id}`}>{s.hostname}</Link></td>
                  <td>{s.primary_ip}</td>
                  <td>{s.os}</td>
                  <td>{s.agent_status === 'ok'
                    ? <span className="badge ok">{s.agent_status}</span>
                    : <span className="badge muted">{s.agent_status}</span>}</td>
                </tr>))}
            </tbody>
          </table>
        </div>)}
      <h2>Alertas activas ({al.length})</h2>
      {msg && <div className="error">{msg}</div>}
      {al.length === 0 ? <p className="empty">Sin alertas activas.</p> : (
        <div className="panel">
          <table className="grid">
            <thead><tr><th>Severidad</th><th>Alcance</th><th>Valor/Umbral</th><th>Acciones</th></tr></thead>
            <tbody>
              {al.map((a: any) => (
                <tr key={a.id}>
                  <td>{sevBadge(a.severity)}</td>
                  <td>{a.scope}</td>
                  <td>{a.value ?? '-'} / {a.threshold ?? '-'}</td>
                  <td>
                    <button className="ghost" onClick={() => act(a.id, 'ack')}>Aceptar</button>{' '}
                    <button className="ghost" onClick={() => act(a.id, 'resolve')}>Resolver</button>
                  </td>
                </tr>))}
            </tbody>
          </table>
        </div>)}
    </div>
  );
}
