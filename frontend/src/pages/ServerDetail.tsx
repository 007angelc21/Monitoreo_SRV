import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import { SeriesChart } from '../components/Chart';

const RANGES = ['15m', '1h', '6h', '24h', '7d', '30d'];

export function ServerDetail() {
  const { id } = useParams();
  const [range, setRange] = useState('1h');
  const { data: srv } = useQuery({ queryKey: ['srv', id], queryFn: async () => (await api.get(`/api/servers/${id}`)).data });
  const { data: m } = useQuery({ queryKey: ['m', id, range], queryFn: async () => (await api.get(`/api/servers/${id}/metrics?range=${range}`)).data });
  const { data: svc } = useQuery({ queryKey: ['svc', id], queryFn: async () => (await api.get(`/api/servers/${id}/services`)).data, refetchInterval: 30000 });
  const services: any[] = svc?.services ?? [];
  return (
    <div>
      <Link className="back" to="/">Volver al panel general</Link>
      <h1>{srv?.hostname ?? 'Servidor'}</h1>
      <p className="meta">IP {srv?.primary_ip} · Sistema {srv?.os} · Agente {srv?.agent_status}
        {srv?.vm && <> · VM <strong>{srv.vm.name}</strong> (enlace {srv.vm.method}, confianza {srv.vm.confidence}%)</>}</p>
      <div className="toolbar">
        <span className="meta">Rango:</span>
        {RANGES.map(r => <button key={r} className="ghost" onClick={() => setRange(r)} disabled={r === range}>{r}</button>)}
        {m?.source && <span className="meta">Fuente: {Object.values(m.source)[0] === 'db' ? 'histórico BD' : 'tiempo real'}</span>}
      </div>
      <SeriesChart title="CPU" unit="%" series={m?.series?.cpu} />
      <SeriesChart title="Memoria RAM" unit="%" series={m?.series?.ram} />
      <SeriesChart title="Disco" unit="%" series={m?.series?.disk} />
      <SeriesChart title="Carga (load 1m)" series={m?.series?.load1} />
      <SeriesChart title="Red entrante" unit="B/s" series={m?.series?.net_rx} />
      <SeriesChart title="Red saliente" unit="B/s" series={m?.series?.net_tx} />
      <h2>Servicios systemd</h2>
      {services.length === 0 ? <p className="empty">Sin servicios supervisados o sin datos.</p> : (
        <div className="panel">
          <table className="grid">
            <thead><tr><th>Unidad</th><th>Estado</th><th>Actividad</th></tr></thead>
            <tbody>
              {services.map((s: any) => (
                <tr key={s.unit}>
                  <td>{s.unit}</td>
                  <td><span className="badge muted">{s.state}</span></td>
                  <td>{s.active
                    ? <span className="badge ok">Activo</span>
                    : <span className="badge crit">Detenido</span>}</td>
                </tr>))}
            </tbody>
          </table>
        </div>)}
    </div>
  );
}
