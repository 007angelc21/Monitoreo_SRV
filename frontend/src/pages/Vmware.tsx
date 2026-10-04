import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api/client';

function powerBadge(p: string) {
  return p === 'POWERED_ON'
    ? <span className="badge ok">Encendida</span>
    : <span className="badge muted">Apagada</span>;
}

function usageBar(pct: number) {
  const cls = pct >= 95 ? 'usage critical' : pct >= 85 ? 'usage high' : 'usage';
  return (
    <div className="usagerow">
      <div className={cls}><span style={{ width: `${Math.min(pct, 100)}%` }} /></div>
      <span>{pct}%</span>
    </div>
  );
}

export function Vmware() {
  const [vc, setVc] = useState('');
  const { data: vcs } = useQuery({ queryKey: ['vcs'], queryFn: async () => (await api.get('/api/vcenters')).data });
  const { data: vms } = useQuery({ queryKey: ['vms', vc], enabled: !!vc, queryFn: async () => (await api.get(`/api/vcenters/${vc}/vms?limit=100`)).data });
  const { data: hosts } = useQuery({ queryKey: ['hosts', vc], enabled: !!vc, queryFn: async () => (await api.get(`/api/vcenters/${vc}/hosts?limit=100`)).data });
  const { data: ds } = useQuery({ queryKey: ['ds', vc], enabled: !!vc, queryFn: async () => (await api.get(`/api/vcenters/${vc}/datastores`)).data });
  const vmItems: any[] = vms?.items ?? [];
  const on = vmItems.filter((v: any) => v.power_state === 'POWERED_ON').length;
  return (
    <div>
      <Link className="back" to="/">Volver al panel general</Link>
      <h1>Infraestructura VMware</h1>
      <div className="toolbar">
        <label htmlFor="vc">vCenter</label>
        <select id="vc" value={vc} onChange={e => setVc(e.target.value)}>
          <option value="">Seleccione un vCenter</option>
          {(vcs ?? []).map((v: any) => <option key={v.id} value={v.id}>{v.name} ({v.status})</option>)}
        </select>
      </div>
      {vc && <>
        <div className="cards">
          <div className="card ok"><div className="t">VMs encendidas</div><div className="v">{on}</div></div>
          <div className="card"><div className="t">VMs totales</div><div className="v">{vms?.total ?? 0}</div></div>
          <div className="card"><div className="t">Hosts ESXi</div><div className="v">{hosts?.total ?? 0}</div></div>
          <div className="card"><div className="t">Datastores</div><div className="v">{(ds ?? []).length}</div></div>
        </div>
        <h2>Máquinas virtuales</h2>
        <div className="panel">
          <table className="grid">
            <thead><tr><th>VM</th><th>Estado</th><th>vCPU</th><th>RAM (MB)</th><th>Snapshots</th></tr></thead>
            <tbody>
              {vmItems.map((v: any) => (
                <tr key={v.id}>
                  <td>{v.name}</td>
                  <td>{powerBadge(v.power_state)}</td>
                  <td>{v.cpu}</td>
                  <td>{v.mem_mb}</td>
                  <td>{v.snapshots > 0
                    ? <span className="badge warn">{v.snapshots} ({v.oldest_snapshot_days}d)</span>
                    : <span className="badge muted">0</span>}</td>
                </tr>))}
            </tbody>
          </table>
        </div>
        <h2>Hosts ESXi</h2>
        <div className="panel">
          <table className="grid">
            <thead><tr><th>Host</th><th>Conexión</th><th>Energía</th></tr></thead>
            <tbody>
              {(hosts?.items ?? []).map((h: any) => (
                <tr key={h.id}>
                  <td>{h.name}</td>
                  <td>{h.connection === 'connected'
                    ? <span className="badge ok">{h.connection}</span>
                    : <span className="badge crit">{h.connection}</span>}</td>
                  <td>{h.power}</td>
                </tr>))}
            </tbody>
          </table>
        </div>
        <h2>Datastores</h2>
        <div className="panel">
          <table className="grid">
            <thead><tr><th>Datastore</th><th>Tipo</th><th>Uso</th></tr></thead>
            <tbody>
              {(ds ?? []).map((d: any) => (
                <tr key={d.id}>
                  <td>{d.name}</td>
                  <td>{d.type}</td>
                  <td>{usageBar(d.used_pct)}</td>
                </tr>))}
            </tbody>
          </table>
        </div>
      </>}
    </div>
  );
}
