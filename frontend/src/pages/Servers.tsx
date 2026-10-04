import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api/client';

const OS_OPTS = ['Ubuntu 24.04', 'Ubuntu 22.04', 'Debian 12', 'Debian 11', 'RHEL 9', 'Rocky 9', 'Otro'];

function apiError(e: any, fallback: string) {
  return e?.response?.data?.error?.message ?? fallback;
}

export function Servers() {
  const qc = useQueryClient();
  const { data: servers } = useQuery({ queryKey: ['servers'], queryFn: async () => (await api.get('/api/servers?limit=200')).data });
  const [hostname, setHostname] = useState('');
  const [ip, setIp] = useState('');
  const [uuid, setUuid] = useState('');
  const [os, setOs] = useState(OS_OPTS[0]);
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(''); setOk('');
    if (!hostname.trim()) { setErr('El nombre del servidor es obligatorio.'); return; }
    if (ip && !/^\d{1,3}(\.\d{1,3}){3}$/.test(ip.trim())) { setErr('La IP no tiene formato válido (ej. 10.0.1.15).'); return; }
    setSaving(true);
    try {
      await api.post('/api/servers', {
        hostname: hostname.trim(),
        primary_ip: ip.trim() || null,
        system_uuid: uuid.trim() || null,
        os,
      });
      setOk(`Servidor "${hostname.trim()}" agregado. Instale Node Exporter y verifique el scrape en Prometheus.`);
      setHostname(''); setIp(''); setUuid('');
      qc.invalidateQueries({ queryKey: ['servers'] });
    } catch (e) {
      setErr(apiError(e, 'No se pudo registrar el servidor.'));
    } finally {
      setSaving(false);
    }
  }

  const items: any[] = servers?.items ?? [];
  return (
    <div>
      <Link className="back" to="/">Volver al panel general</Link>
      <h1>Servidores en monitoreo</h1>
      <div className="panel">
        <h3>Agregar servidor</h3>
        <form onSubmit={submit}>
          <div className="toolbar">
            <div>
              <label htmlFor="f-host">Nombre *</label><br />
              <input id="f-host" placeholder="web01" value={hostname} onChange={e => setHostname(e.target.value)} />
            </div>
            <div>
              <label htmlFor="f-ip">IP principal</label><br />
              <input id="f-ip" placeholder="10.0.1.15" value={ip} onChange={e => setIp(e.target.value)} />
            </div>
            <div>
              <label htmlFor="f-os">Sistema operativo</label><br />
              <select id="f-os" value={os} onChange={e => setOs(e.target.value)}>
                {OS_OPTS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="f-uuid">UUID del sistema (para enlazar con vCenter)</label><br />
            <input id="f-uuid" className="wide" placeholder="dmidecode -s system-uuid" value={uuid} onChange={e => setUuid(e.target.value)} />
            <p className="meta">En el servidor: <code>sudo dmidecode -s system-uuid</code>. Debe coincidir con el instanceUuid de la VM para el enlace automático.</p>
          </div>
          <button className="btn" type="submit" disabled={saving}>{saving ? 'Guardando...' : 'Agregar al monitoreo'}</button>
        </form>
        {err && <div className="error">{err}</div>}
        {ok && <p className="okmsg">{ok}</p>}
      </div>
      <h2>Registrados ({servers?.total ?? items.length})</h2>
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
    </div>
  );
}
