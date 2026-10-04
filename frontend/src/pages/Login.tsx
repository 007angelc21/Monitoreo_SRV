import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const nav = useNavigate();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr('');
    try {
      const form = new URLSearchParams({ username: email, password });
      const r = await api.post('/api/auth/login', form, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
      localStorage.setItem('token', r.data.access_token);
      nav('/');
    } catch {
      setErr('Credenciales inválidas. Verifique usuario y contraseña.');
    }
  }
  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>Monitoreo SRV</h1>
        <p className="sub">Plataforma centralizada · Linux + VMware vCenter</p>
        <form onSubmit={submit}>
          <label htmlFor="email">Usuario</label>
          <input id="email" placeholder="usuario@empresa.com" value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" />
          <label htmlFor="pass">Contraseña</label>
          <input id="pass" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" />
          <button className="btn" type="submit">Iniciar sesión</button>
        </form>
        {err && <div className="error">{err}</div>}
      </div>
    </div>
  );
}
