import { HashRouter, Routes, Route, Link, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { Overview } from './pages/Overview';
import { Maintenance } from './pages/Maintenance';
import { Servers } from './pages/Servers';
import { ServerDetail } from './pages/ServerDetail';
import { Vmware } from './pages/Vmware';
import { Login } from './pages/Login';

function guard(el: JSX.Element) {
  return localStorage.getItem('token') ? el : <Navigate to="/login" />;
}

function Shell() {
  const nav = useNavigate();
  const logged = !!localStorage.getItem('token');
  function logout() {
    localStorage.removeItem('token');
    nav('/login');
  }
  return (
    <>
      <header className="topbar">
        <div className="brand">Monitoreo SRV<small>Linux + VMware vCenter</small></div>
        <nav>
          <NavLink end to="/">General</NavLink>
          <NavLink to="/servers">Servidores</NavLink>
          <NavLink to="/vmware">VMware</NavLink>
          <NavLink to="/maintenance">Mantenimiento</NavLink>
        </nav>
        <div className="spacer" />
        {logged && <button onClick={logout}>Cerrar sesión</button>}
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={guard(<Overview />)} />
          <Route path="/servers" element={guard(<Servers />)} />
          <Route path="/maintenance" element={guard(<Maintenance />)} />
          <Route path="/servers/:id" element={guard(<ServerDetail />)} />
          <Route path="/vmware" element={guard(<Vmware />)} />
          <Route path="/login" element={<Login />} />
        </Routes>
      </main>
    </>
  );
}

export function App() {
  return (
    <HashRouter>
      <Shell />
    </HashRouter>
  );
}
