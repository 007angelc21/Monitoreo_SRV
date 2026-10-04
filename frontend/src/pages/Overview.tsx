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
    <div className="overview">
      <header className="overview-heading">
        <div>
          <p className="eyebrow">Centro de operaciones</p>
          <h1>Panel general</h1>
          <p className="heading-copy">Estado actual de servidores, alertas y virtualización.</p>
        </div>
        <Link className="btn" to="/servers">Agregar servidor</Link>
      </header>
      <div className="cards" aria-label="Resumen de infraestructura">
        <div className="card metric-card servers-card"><div className="t">Servidores</div><div className="v">{servers?.total ?? items.length}</div><div className="metric-note">En monitoreo</div></div>
        <div className="card metric-card crit"><div className="t">Críticas</div><div className="v">{crit}</div><div className="metric-note">Requieren atención</div></div>
        <div className="card metric-card warn"><div className="t">Advertencias</div><div className="v">{warn}</div><div className="metric-note">Alertas activas</div></div>
        <div className="card metric-card vc-card"><div className="t">vCenters</div><div className="v">{(vcs ?? []).length}</div><div className="metric-note">Conectados</div></div>
      </div>
      <section className="overview-section">
        <div className="section-heading">
          <div><p className="eyebrow">Inventario</p><h2>Servidores</h2></div>
          <span className="section-count">{servers?.total ?? items.length} registrados</span>
        </div>
        {items.length === 0 ? <p className="empty empty-panel">Sin servidores registrados.</p> : (
        <div className="panel table-panel">
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
      </section>
      <section className="overview-section">
        <div className="section-heading">
          <div><p className="eyebrow">Eventos</p><h2>Alertas activas</h2></div>
          <span className="section-count">{al.length} abiertas</span>
        </div>
        {al.length === 0 ? <p className="empty empty-panel">Sin alertas activas.</p> : (
        <div className="panel table-panel">
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
      </section>
    </div>
  );
}
