import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import { SeriesChart } from '../components/Chart';

const RANGES = ['15m', '1h', '6h', '24h', '7d', '30d'];

function fmtBytes(b: number) {
  if (b >= 1024 ** 3) return `${(b / 1024 ** 3).toFixed(1)} GB`;
  if (b >= 1024 ** 2) return `${(b / 1024 ** 2).toFixed(0)} MB`;
  return `${Math.round(b / 1024)} KB`;
}

function DiskUsage({ id }: { id: string }) {
  const { data } = useQuery({ queryKey: ['du', id], queryFn: async () => (await api.get(`/api/servers/${id}/diskusage?limit=12`)).data, refetchInterval: 300000 });
  const rows: any[] = data?.top ?? [];
  if (!rows.length) return <p className="empty">{data?.note ?? 'Sin datos.'}</p>;
  const max = Math.max(...rows.map((r: any) => r.bytes), 1);
  return (
    <div className="panel">
      {data?.synthetic && <div className="toolbar"><span className="badge warn">Datos de prueba</span></div>}
      <table className="grid">
        <thead><tr><th>Carpeta</th><th>Tamaño</th></tr></thead>
        <tbody>
          {rows.map((r: any) => (
            <tr key={r.path}>
              <td><code>{r.path}</code></td>
              <td><div className="usagerow"><div className="usage"><span style={{ width: `${Math.round((r.bytes / max) * 100)}%` }} /></div><span>{fmtBytes(r.bytes)}</span></div></td>
            </tr>))}
        </tbody>
      </table>
    </div>
  );
}

function TopApps({ id }: { id: string }) {
  const [kind, setKind] = useState<'cpu' | 'mem'>('cpu');
  const { data } = useQuery({ queryKey: ['top', id], queryFn: async () => (await api.get(`/api/servers/${id}/top?limit=10`)).data, refetchInterval: 60000 });
  const rows: any[] = [...(data?.top ?? [])].sort((a, b) => (kind === 'cpu' ? b.cpu - a.cpu : b.mem - a.mem));
  if (!rows.length) return <p className="empty">{data?.note ?? 'Sin datos.'}</p>;
  return (
    <div className="panel">
      <div className="toolbar">
        {data?.synthetic && <span className="badge warn">Datos de prueba</span>}
        <span className="meta">Ordenar por:</span>
        <button className="ghost" disabled={kind === 'cpu'} onClick={() => setKind('cpu')}>CPU</button>
        <button className="ghost" disabled={kind === 'mem'} onClick={() => setKind('mem')}>Memoria</button>
      </div>
      <table className="grid">
        <thead><tr><th>Aplicación</th><th>CPU %</th><th>Mem %</th><th>Procesos</th></tr></thead>
        <tbody>
          {rows.map((r: any) => (
            <tr key={r.app}>
              <td>{r.app}</td>
              <td><div className="usagerow"><div className="usage"><span style={{ width: `${Math.min(r.cpu, 100)}%` }} /></div><span>{r.cpu.toFixed(1)}</span></div></td>
              <td><div className="usagerow"><div className="usage"><span style={{ width: `${Math.min(r.mem, 100)}%` }} /></div><span>{r.mem.toFixed(1)}</span></div></td>
              <td>{r.processes}</td>
            </tr>))}
        </tbody>
      </table>
    </div>
  );
}

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
      <h2>Top aplicaciones</h2>
      <TopApps id={id!} />
      <h2>Top carpetas por espacio</h2>
      <DiskUsage id={id!} />
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
