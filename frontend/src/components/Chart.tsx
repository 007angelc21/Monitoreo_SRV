import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export function SeriesChart({ title, series, unit }: { title: string; series: any; unit?: string }) {
  const rows: any[] = Array.isArray(series) ? series : [];
  // Une múltiples series Prometheus en puntos por timestamp
  const byTs = new Map<number, any>();
  rows.forEach((s, i) => {
    (s.values ?? []).forEach((p: any[]) => {
      const t = p[0], v = Number(p[1]);
      if (!byTs.has(t)) byTs.set(t, { t: new Date(t * 1000).toLocaleTimeString() });
      byTs.get(t)[`v${i}`] = isNaN(v) ? null : Math.round(v * 100) / 100;
    });
  });
  const data = [...byTs.entries()].sort((a, b) => a[0] - b[0]).map(([, o]) => o);
  const keys = rows.map((_, i) => `v${i}`);
  const colors = ['#2563eb', '#16a34a', '#dc2626', '#d97706'];
  return (
    <div className="panel">
      <h3>{title}{unit ? ` (${unit})` : ''}</h3>
      {data.length === 0 ? <p className="empty">Sin datos en el rango.</p> : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="t" minTickGap={50} /><YAxis /><Tooltip />
            {keys.map((k, i) => <Line key={k} type="monotone" dataKey={k} stroke={colors[i % colors.length]} dot={false} />)}
          </LineChart>
        </ResponsiveContainer>)}
    </div>
  );
}
