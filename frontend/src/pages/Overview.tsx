import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '../api/client';

function sevBadge(s: string) {
  const k = s === 'CRITICAL' ? 'crit' : s === 'WARNING' ? 'warn' : 'info';
  return <span className={`badge ${k}`}>{s}</span>;
}

export function Overview() {
  const { data: servers } = useQuery({ queryKey: ['servers'], queryFn: async () => (await api.get('/api/servers')).data });
  const { data: alerts } = useQuery({ queryKey: ['alerts'], queryFn: async () => (await api.get('/api/alerts?status=firing')).data, refetchInterval: 15000 });
  const { data: vcs } = useQuery({ queryKey: ['vcs'], queryFn: async () => (await api.get('/api/vcenters')).data });
  const items: any[] = servers?.items ?? [];
  const al: any[] = alerts?.items ?? alerts ?? [];
  const crit = al.filter(a => a.severity === 'CRITICAL').length;
  const warn = al.filter(a => a.severity !== 'CRITICAL').length;
  return (
    <div>
      <h1>Panel general</h1>
      <div className="cards">
        <div className="card"><div className="t">Servidores</div><div className="v">{servers?.total ?? items.length}</div></div>
        <div className="card crit"><div className="t">Críticas</div><div className="v">{crit}</div></div>
        <div className="card warn"><div className="t">Advertencias</div><div className="v">{warn}</div></div>
        <div className="card"><div className="t">vCenters</div><div className="v">{(vcs ?? []).length}</div></div>
      </div>
      <h2>Servidores</h2>
      <p><Link className="btn" to="/servers">Agregar servidor</Link></p>
      {items.length === 0 ? <p className="empty">Sin servidores registrados.</p> : (
        <div className="panel">
          <table className="grid">
            <thead><tr><th>Servidor</th><th>IP</th><th>Estado agente</th></tr></thead>
            <tbody>
              {items.map((s: any) => (
                <tr key={s.id}>
                  <td><Link to={`/servers/${s.id}`}>{s.hostname}</Link></td>
                  <td>{s.primary_ip}</td>
                  <td>{s.agent_status === 'ok'
                    ? <span className="badge ok">{s.agent_status}</span>
                    : <span className="badge muted">{s.agent_status}</span>}</td>
                </tr>))}
            </tbody>
          </table>
        </div>)}
      <h2>Alertas activas</h2>
      {al.length === 0 ? <p className="empty">Sin alertas activas.</p> : (
        <div className="panel">
          <table className="grid">
            <thead><tr><th>Severidad</th><th>Alcance</th><th>Duplicadas</th></tr></thead>
            <tbody>
              {al.map((a: any) => (
                <tr key={a.id}>
                  <td>{sevBadge(a.severity)}</td>
                  <td>{a.scope}</td>
                  <td>{a.dedup}</td>
                </tr>))}
            </tbody>
          </table>
        </div>)}
    </div>
  );
}
