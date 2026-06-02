import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { clearAccessToken, apiFetch } from '../api/client'
import styles from './Layout.module.css'

export default function Layout({ onLogout }) {
  const navigate = useNavigate()

  async function handleLogout() {
    await apiFetch('/auth/logout', { method: 'POST' }).catch(() => {})
    clearAccessToken()
    onLogout()
    navigate('/login')
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>⚙️</span>
          <div>
            <div className={styles.logoTitle}>Motor MIMIC-IV</div>
            <div className={styles.logoBadge}>Painel Admin</div>
          </div>
        </div>
        <nav className={styles.nav}>
          <NavLink to="/" end className={({ isActive }) => isActive ? styles.navLinkActive : styles.navLink}>
            📊 Dashboard
          </NavLink>
          <NavLink to="/plugins" className={({ isActive }) => isActive ? styles.navLinkActive : styles.navLink}>
            🔌 Plugins
          </NavLink>
          <NavLink to="/regras" className={({ isActive }) => isActive ? styles.navLinkActive : styles.navLink}>
            📋 Regras Clínicas
          </NavLink>
        </nav>
        <button className={styles.logoutBtn} onClick={handleLogout}>
          ↩ Sair
        </button>
      </aside>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
